import csv
import io
import unicodedata
import uuid
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, cast

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, ValidationError
from sqlalchemy import Date, String, func, or_, select, true
from sqlalchemy import cast as sql_cast

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes import equipment as equipment_routes
from app.api.routes import expenses as expenses_routes
from app.api.routes import fuel as fuel_routes
from app.api.routes import inventory as inventory_routes
from app.api.routes import notes as notes_routes
from app.api.routes import plans as plans_routes
from app.api.routes import work_records as work_records_routes
from app.db.filters import active
from app.models import (
    Equipment,
    ExpenseRecord,
    FuelRecord,
    Inspection,
    InventoryItem,
    Note,
    Plan,
    Role,
    SavedView,
    Vehicle,
    WorkRecord,
)
from app.schemas.equipment import EquipmentUpdate
from app.schemas.expenses import ExpenseRecordUpdate
from app.schemas.fuel import FuelRecordUpdate
from app.schemas.inventory import InventoryItemUpdate
from app.schemas.notes import NoteUpdate
from app.schemas.plans import PlanUpdate
from app.schemas.saved_view import SavedViewIn, SavedViewOut
from app.schemas.search import (
    BulkFailure,
    BulkOperationIn,
    BulkOperationResult,
    SearchKind,
    SearchResult,
    SearchSort,
)
from app.schemas.work_records import WorkRecordUpdate

router = APIRouter(prefix="/search", tags=["search"])
_ACCENTS = "áàâãäéèêëíìîïóòôõöúùûüçñýÿ"
_ASCII = "aaaaaeeeeiiiiooooouuuucnyy"

_KNOWN_KINDS: frozenset[str] = frozenset(
    {"vehicle", "fuel", "work", "expense", "note", "plan", "inventory", "equipment", "inspection"}
)
_SECTIONS = {"fuel": "fuel", "work": "work", "expense": "expenses", "note": "notes"}

# Household-level records (vehicle, inventory) are scoped by `household_id`
# directly; every other kind is reached through the vehicle it belongs to.
_HOUSEHOLD_SCOPED_KINDS = {"inventory", "vehicle"}

_ALL_MODELS: dict[str, type] = {
    "vehicle": Vehicle,
    "fuel": FuelRecord,
    "work": WorkRecord,
    "expense": ExpenseRecord,
    "note": Note,
    "plan": Plan,
    "equipment": Equipment,
    "inventory": InventoryItem,
    "inspection": Inspection,
}

_ROLE_GATES: dict[str, set[Role]] = {
    "fuel": fuel_routes._CAN_WRITE_RECORDS,
    "work": work_records_routes._CAN_WRITE_RECORDS,
    "expense": expenses_routes._CAN_WRITE,
    "note": notes_routes._CAN_WRITE,
    "plan": plans_routes._CAN_WRITE,
    "equipment": equipment_routes._CAN_WRITE,
    "inventory": inventory_routes._CAN_WRITE,
}

_UPDATE_SCHEMAS: dict[str, type[BaseModel]] = {
    "fuel": FuelRecordUpdate,
    "work": WorkRecordUpdate,
    "expense": ExpenseRecordUpdate,
    "note": NoteUpdate,
    "plan": PlanUpdate,
    "equipment": EquipmentUpdate,
    "inventory": InventoryItemUpdate,
}

# Vehicles are managed through their own dedicated (soft-delete) flow and
# inspections are immutable once completed (spec §16/§17) — neither is ever
# mutated in bulk, only read for export.
_DELETE_KINDS = {"fuel", "work", "expense", "note", "plan", "equipment", "inventory"}
_DUPLICATE_KINDS = _DELETE_KINDS
_MOVE_KINDS = {"fuel", "work", "expense", "note", "plan", "equipment"}
_EDIT_KINDS = _DELETE_KINDS


def _term(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _matches(*columns: Any, term: str) -> Any:
    if not term:
        return true()
    pattern = f"%{term}%"
    return or_(
        *(
            func.translate(func.lower(sql_cast(column, String)), _ACCENTS, _ASCII).like(pattern)
            for column in columns
        )
    )


def _vehicle_result(item: Vehicle) -> SearchResult:
    return SearchResult(
        id=item.id,
        kind="vehicle",
        title=item.name,
        subtitle=" · ".join(
            value for value in (item.make, item.model, item.license_plate) if value
        ),
        vehicle_id=item.id,
        occurred_on=item.created_at,
        url=f"/vehicles/{item.id}",
    )


def _build_result(kind: str, item: Any, vehicle_names: dict[uuid.UUID, str]) -> SearchResult:
    vehicle_id = getattr(item, "vehicle_id", None)
    resolved_vehicle_id = vehicle_id if isinstance(vehicle_id, uuid.UUID) else None
    if kind == "fuel":
        title, subtitle, occurred = (
            item.station or item.fuel_type or "Fuel",
            item.notes,
            item.recorded_on,
        )
    elif kind == "work":
        title, subtitle, occurred = item.description, item.supplier, item.recorded_on
    elif kind == "expense":
        title, subtitle, occurred = item.category, item.supplier, item.issued_on
    elif kind == "note":
        title, subtitle, occurred = item.title, item.content[:160], item.created_at
    elif kind == "plan":
        title, subtitle, occurred = (
            item.description,
            item.notes,
            item.due_date or item.created_at,
        )
    elif kind == "inventory":
        title, subtitle, occurred = (
            item.name,
            item.reference or item.manufacturer,
            item.created_at,
        )
    elif kind == "equipment":
        title, subtitle, occurred = (
            item.name,
            item.model or item.manufacturer,
            item.created_at,
        )
    else:
        title = item.template_snapshot.get("name", "Inspection")
        subtitle, occurred = item.notes, item.recorded_on
    if kind in _SECTIONS:
        url = f"/vehicles/{vehicle_id}?section={_SECTIONS[kind]}"
    elif kind == "plan":
        url = "/planner"
    elif kind == "inventory":
        url = "/inventory"
    elif kind == "equipment":
        url = "/equipment"
    else:
        url = "/inspections"
    vehicle_name = vehicle_names.get(resolved_vehicle_id) if resolved_vehicle_id else None
    return SearchResult(
        id=item.id,
        kind=cast(SearchKind, kind),
        title=title,
        subtitle=(
            f"{vehicle_name} · {subtitle}"
            if subtitle and resolved_vehicle_id
            else subtitle or vehicle_name
        ),
        vehicle_id=resolved_vehicle_id,
        occurred_on=occurred,
        url=url,
    )


@router.get("", response_model=list[SearchResult])
async def global_search(
    membership: CurrentMembership,
    db: DbSession,
    q: str | None = Query(default=None, min_length=2, max_length=100),
    kind: Annotated[list[str] | None, Query()] = None,
    vehicle_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: SearchSort = "occurred_on_desc",
) -> list[SearchResult]:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    requested_kinds = set(kind) if kind else None
    if requested_kinds and not requested_kinds.issubset(_KNOWN_KINDS):
        raise HTTPException(status_code=422, detail="Unknown kind filter")
    term = _term(q.strip()) if q else ""

    if vehicle_id:
        matched = set(
            await db.scalars(
                select(Vehicle.id).where(
                    Vehicle.household_id == membership.household_id,
                    Vehicle.deleted_at.is_(None),
                    Vehicle.id.in_(vehicle_id),
                )
            )
        )
        if matched != set(vehicle_id):
            raise HTTPException(status_code=404, detail="One or more vehicles were not found")

    def _wants(entity_kind: str) -> bool:
        return requested_kinds is None or entity_kind in requested_kinds

    def _dated(query: Any, column: Any) -> Any:
        if date_from:
            query = query.where(column >= date_from)
        if date_to:
            query = query.where(column <= date_to)
        return query

    per_kind_limit = 20 if term else 50

    household_vehicle_ids = select(Vehicle.id).where(
        Vehicle.household_id == membership.household_id, Vehicle.deleted_at.is_(None)
    )
    if vehicle_id:
        household_vehicle_ids = household_vehicle_ids.where(Vehicle.id.in_(vehicle_id))

    vehicles: list[Vehicle] = []
    if _wants("vehicle"):
        vehicle_query = select(Vehicle).where(
            Vehicle.household_id == membership.household_id,
            Vehicle.deleted_at.is_(None),
            _matches(
                Vehicle.name,
                Vehicle.make,
                Vehicle.model,
                Vehicle.license_plate,
                Vehicle.vin,
                term=term,
            ),
        )
        if vehicle_id:
            vehicle_query = vehicle_query.where(Vehicle.id.in_(vehicle_id))
        vehicle_query = _dated(vehicle_query, Vehicle.created_at).limit(per_kind_limit)
        vehicles = list(await db.scalars(vehicle_query))

    queries: list[tuple[str, Any]] = []
    if _wants("fuel"):
        fuel_query = select(FuelRecord).where(
            FuelRecord.vehicle_id.in_(household_vehicle_ids),
            active(FuelRecord),
            _matches(FuelRecord.station, FuelRecord.fuel_type, FuelRecord.notes, term=term),
        )
        queries.append(("fuel", _dated(fuel_query, FuelRecord.recorded_on).limit(per_kind_limit)))
    if _wants("work"):
        work_query = select(WorkRecord).where(
            WorkRecord.vehicle_id.in_(household_vehicle_ids),
            active(WorkRecord),
            _matches(WorkRecord.description, WorkRecord.supplier, WorkRecord.notes, term=term),
        )
        queries.append(("work", _dated(work_query, WorkRecord.recorded_on).limit(per_kind_limit)))
    if _wants("expense"):
        expense_query = select(ExpenseRecord).where(
            ExpenseRecord.vehicle_id.in_(household_vehicle_ids),
            active(ExpenseRecord),
            _matches(ExpenseRecord.category, ExpenseRecord.supplier, term=term),
        )
        queries.append(
            ("expense", _dated(expense_query, ExpenseRecord.issued_on).limit(per_kind_limit))
        )
    if _wants("note"):
        note_query = select(Note).where(
            Note.vehicle_id.in_(household_vehicle_ids),
            active(Note),
            _matches(Note.title, Note.content, term=term),
        )
        queries.append(("note", _dated(note_query, Note.created_at).limit(per_kind_limit)))
    if _wants("plan"):
        plan_query = select(Plan).where(
            Plan.vehicle_id.in_(household_vehicle_ids),
            active(Plan),
            _matches(Plan.description, Plan.notes, term=term),
        )
        plan_date = func.coalesce(Plan.due_date, sql_cast(Plan.created_at, Date))
        queries.append(("plan", _dated(plan_query, plan_date).limit(per_kind_limit)))
    if _wants("inventory"):
        inventory_query = select(InventoryItem).where(
            InventoryItem.household_id == membership.household_id,
            _matches(
                InventoryItem.name,
                InventoryItem.reference,
                InventoryItem.manufacturer,
                InventoryItem.supplier,
                InventoryItem.notes,
                term=term,
            ),
        )
        if vehicle_id:
            inventory_query = inventory_query.where(InventoryItem.vehicle_id.in_(vehicle_id))
        queries.append(
            (
                "inventory",
                _dated(inventory_query, InventoryItem.created_at).limit(per_kind_limit),
            )
        )
    if _wants("equipment"):
        equipment_query = select(Equipment).where(
            Equipment.vehicle_id.in_(household_vehicle_ids),
            _matches(
                Equipment.name,
                Equipment.manufacturer,
                Equipment.model,
                Equipment.notes,
                term=term,
            ),
        )
        queries.append(
            ("equipment", _dated(equipment_query, Equipment.created_at).limit(per_kind_limit))
        )
    if _wants("inspection"):
        inspection_query = select(Inspection).where(
            Inspection.vehicle_id.in_(household_vehicle_ids),
            _matches(Inspection.template_snapshot, Inspection.notes, term=term),
        )
        queries.append(
            (
                "inspection",
                _dated(inspection_query, Inspection.recorded_on).limit(per_kind_limit),
            )
        )

    found = {entity_kind: list(await db.scalars(query)) for entity_kind, query in queries}
    vehicle_names = {
        item.id: item.name
        for item in await db.scalars(
            select(Vehicle).where(Vehicle.id.in_(household_vehicle_ids), active(Vehicle))
        )
    }

    results: list[SearchResult] = [_vehicle_result(item) for item in vehicles]
    for entity_kind, items in found.items():
        for item in items:
            results.append(_build_result(entity_kind, item, vehicle_names))

    def _occurred_key(result: SearchResult) -> str:
        return result.occurred_on.isoformat() if result.occurred_on else ""

    def _title_key(result: SearchResult) -> str:
        return result.title.casefold()

    if sort == "occurred_on_asc":
        results.sort(key=_occurred_key)
    elif sort == "title_asc":
        results.sort(key=_title_key)
    elif sort == "title_desc":
        results.sort(key=_title_key, reverse=True)
    else:
        results.sort(key=_occurred_key, reverse=True)

    return results[:100]


@router.get("/saved-views", response_model=list[SavedViewOut])
async def list_saved_views(membership: CurrentMembership, db: DbSession) -> list[SavedView]:
    result = await db.scalars(
        select(SavedView)
        .where(SavedView.household_id == membership.household_id)
        .order_by(SavedView.created_at.desc())
    )
    return list(result)


@router.post("/saved-views", response_model=SavedViewOut, status_code=status.HTTP_201_CREATED)
async def create_saved_view(
    payload: SavedViewIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> SavedView:
    view = SavedView(
        household_id=membership.household_id, created_by=user.id, **payload.model_dump()
    )
    db.add(view)
    await db.commit()
    await db.refresh(view)
    return view


@router.delete("/saved-views/{view_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_view(
    view_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    view = await db.get(SavedView, view_id)
    if view is None or view.household_id != membership.household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved view not found")
    if view.created_by != user.id and membership.role not in {Role.OWNER, Role.MANAGER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator or an owner/manager can delete another member's saved view",
        )
    await db.delete(view)
    await db.commit()


async def _fetch_owned(
    kind: str,
    item_id: uuid.UUID,
    membership: CurrentMembership,
    db: DbSession,
    vehicle_cache: dict[uuid.UUID, bool],
) -> Any | None:
    model = _ALL_MODELS.get(kind)
    if model is None:
        return None
    record = await db.get(cast(Any, model), item_id)
    if record is None:
        return None
    if kind in _HOUSEHOLD_SCOPED_KINDS:
        if record.household_id != membership.household_id:
            return None
        if kind == "vehicle" and record.deleted_at is not None:
            return None
        return record
    vehicle_id = record.vehicle_id
    if vehicle_id not in vehicle_cache:
        vehicle = await db.get(Vehicle, vehicle_id)
        vehicle_cache[vehicle_id] = bool(
            vehicle is not None
            and vehicle.household_id == membership.household_id
            and vehicle.deleted_at is None
        )
    return record if vehicle_cache[vehicle_id] else None


def _duplicate_fuel(record: Any, user_id: uuid.UUID) -> FuelRecord:
    return FuelRecord(
        vehicle_id=record.vehicle_id,
        created_by=user_id,
        recorded_on=record.recorded_on,
        odometer_reading=record.odometer_reading,
        volume_litres=record.volume_litres,
        total_price=record.total_price,
        unit_price=record.unit_price,
        fuel_type=record.fuel_type,
        station=record.station,
        full_tank=record.full_tank,
        excluded_from_consumption=record.excluded_from_consumption,
        notes=record.notes,
    )


def _duplicate_work(record: Any, user_id: uuid.UUID) -> WorkRecord:
    return WorkRecord(
        vehicle_id=record.vehicle_id,
        created_by=user_id,
        recorded_on=record.recorded_on,
        kind=record.kind,
        description=record.description,
        odometer_reading=record.odometer_reading,
        total_cost=record.total_cost,
        supplier=record.supplier,
        notes=record.notes,
    )


def _duplicate_expense(record: Any, user_id: uuid.UUID) -> ExpenseRecord:
    return ExpenseRecord(
        vehicle_id=record.vehicle_id,
        created_by=user_id,
        issued_on=record.issued_on,
        category=record.category,
        amount=record.amount,
        supplier=record.supplier,
        status=record.status,
    )


def _duplicate_note(record: Any, user_id: uuid.UUID) -> Note:
    return Note(
        vehicle_id=record.vehicle_id,
        created_by=user_id,
        title=record.title,
        content=record.content,
        pinned=record.pinned,
    )


def _duplicate_plan(record: Any, user_id: uuid.UUID) -> Plan:
    return Plan(
        vehicle_id=record.vehicle_id,
        created_by=user_id,
        # A copy of a completed plan starts over: a "completed" stage only
        # makes sense alongside the original's own completed_work_record_id.
        stage="planned" if record.stage == "completed" else record.stage,
        kind=record.kind,
        priority=record.priority,
        description=record.description,
        estimated_cost=record.estimated_cost,
        due_date=record.due_date,
        due_odometer=record.due_odometer,
        notes=record.notes,
    )


def _duplicate_equipment(record: Any, user_id: uuid.UUID) -> Equipment:
    # Mount/rotation history and the current mount state are deliberately not
    # copied: a duplicate is a new physical item, not a continuation of one.
    return Equipment(
        vehicle_id=record.vehicle_id,
        created_by=user_id,
        name=record.name,
        kind=record.kind,
        status="stored",
        manufacturer=record.manufacturer,
        model=record.model,
        serial_number=record.serial_number,
        tire_size=record.tire_size,
        tire_dot=record.tire_dot,
        tread_depth_mm=record.tread_depth_mm,
        season=record.season,
        notes=record.notes,
    )


def _duplicate_inventory(record: Any, user_id: uuid.UUID) -> InventoryItem:
    # A copy of a physical item starts at zero stock, not the source's count.
    return InventoryItem(
        household_id=record.household_id,
        created_by=user_id,
        vehicle_id=record.vehicle_id,
        name=record.name,
        reference=record.reference,
        manufacturer=record.manufacturer,
        quantity=Decimal(0),
        unit=record.unit,
        unit_cost=record.unit_cost,
        minimum_quantity=record.minimum_quantity,
        location=record.location,
        supplier=record.supplier,
        notes=record.notes,
    )


_DUPLICATORS: dict[str, Callable[[Any, uuid.UUID], Any]] = {
    "fuel": _duplicate_fuel,
    "work": _duplicate_work,
    "expense": _duplicate_expense,
    "note": _duplicate_note,
    "plan": _duplicate_plan,
    "equipment": _duplicate_equipment,
    "inventory": _duplicate_inventory,
}


def _delete_guard(kind: str, record: Any) -> str | None:
    if kind == "plan" and record.stage == "completed":
        return "Completed plans cannot be deleted"
    if kind == "equipment" and record.status == "mounted":
        return "Mounted equipment cannot be deleted"
    if kind == "inventory" and record.quantity != 0:
        return "Stock must be zero before deleting an item"
    return None


async def _apply_delete(kind: str, record: Any, user: CurrentUser, db: DbSession) -> None:
    if kind == "work":
        await work_records_routes._restore_requisitioned_stock(record.id, user.id, db)
    vehicle_id = record.vehicle_id if kind != "inventory" else None
    await db.delete(record)
    await db.flush()
    if kind == "fuel" and vehicle_id is not None:
        await fuel_routes._recalculate_consumption(vehicle_id, db)


def _move_guard(kind: str, record: Any) -> str | None:
    if kind == "equipment" and record.status == "mounted":
        return "Unmount equipment before moving it to another vehicle"
    return None


async def _validate_edit_fields(
    kind: str, changes: dict[str, Any], membership: CurrentMembership, db: DbSession
) -> None:
    if kind == "plan":
        required = {"kind", "description", "priority", "stage"}
        if any(field in changes and changes[field] is None for field in required):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Required plan fields cannot be null",
            )
    if kind == "inventory":
        if any(changes.get(field) is None for field in ("name", "unit") if field in changes):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Name and unit cannot be null",
            )
        target = changes.get("vehicle_id")
        if target:
            vehicle = await db.get(Vehicle, target)
            if (
                vehicle is None
                or vehicle.household_id != membership.household_id
                or vehicle.deleted_at is not None
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Target vehicle not found",
                )


def _edit_item_guard(kind: str, record: Any, changes: dict[str, Any]) -> str | None:
    if kind == "plan" and record.stage == "completed":
        return "Completed plans must be corrected through their work record"
    if kind == "equipment" and record.status == "mounted" and "status" in changes:
        return "Unmount equipment before changing its status"
    return None


async def _bulk_export(
    payload: BulkOperationIn, membership: CurrentMembership, db: DbSession
) -> Response:
    vehicle_cache: dict[uuid.UUID, bool] = {}
    household_vehicle_ids = select(Vehicle.id).where(
        Vehicle.household_id == membership.household_id
    )
    vehicle_names = {
        item.id: item.name
        for item in await db.scalars(
            select(Vehicle).where(Vehicle.id.in_(household_vehicle_ids), active(Vehicle))
        )
    }
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["kind", "title", "subtitle", "vehicle", "occurred_on", "url"])
    for item in payload.items:
        record = await _fetch_owned(item.kind, item.id, membership, db, vehicle_cache)
        if record is None:
            continue
        result = (
            _vehicle_result(record)
            if item.kind == "vehicle"
            else _build_result(item.kind, record, vehicle_names)
        )
        vehicle_name = vehicle_names.get(result.vehicle_id) if result.vehicle_id else None
        writer.writerow(
            [
                result.kind,
                result.title,
                result.subtitle or "",
                vehicle_name or "",
                result.occurred_on.isoformat() if result.occurred_on else "",
                result.url,
            ]
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="rodiva-search-export.csv"'},
    )


@router.post("/bulk", response_model=None)
async def bulk_operation(
    payload: BulkOperationIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> BulkOperationResult | Response:
    if payload.operation == "export":
        return await _bulk_export(payload, membership, db)

    allowed: dict[str, set[str]] = {
        "delete": _DELETE_KINDS,
        "duplicate": _DUPLICATE_KINDS,
        "move": _MOVE_KINDS,
        "edit": _EDIT_KINDS,
    }
    allowed_kinds = allowed[payload.operation]

    target_vehicle: Vehicle | None = None
    if payload.operation == "move":
        if payload.target_vehicle_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="target_vehicle_id is required for move",
            )
        target_vehicle = await db.get(Vehicle, payload.target_vehicle_id)
        if (
            target_vehicle is None
            or target_vehicle.household_id != membership.household_id
            or target_vehicle.deleted_at is not None
        ):
            raise HTTPException(status_code=404, detail="Target vehicle not found")

    changes: dict[str, Any] = {}
    edit_kind: str | None = None
    if payload.operation == "edit":
        kinds_present = {item.kind for item in payload.items}
        if len(kinds_present) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="All selected items must share the same kind to bulk-edit",
            )
        (edit_kind,) = kinds_present
        if edit_kind not in _EDIT_KINDS or not payload.fields:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Editing '{edit_kind}' records is not supported",
            )
        schema = _UPDATE_SCHEMAS[edit_kind]
        try:
            update_model = schema.model_validate(payload.fields)
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error.errors()
            ) from error
        changes = update_model.model_dump(exclude_unset=True)
        await _validate_edit_fields(edit_kind, changes, membership, db)

    vehicle_cache: dict[uuid.UUID, bool] = {}
    failures: list[BulkFailure] = []
    succeeded = 0

    for item in payload.items:
        if item.kind not in allowed_kinds:
            failures.append(
                BulkFailure(
                    kind=item.kind,
                    id=item.id,
                    reason=f"Operation not supported for '{item.kind}'",
                )
            )
            continue
        record = await _fetch_owned(item.kind, item.id, membership, db, vehicle_cache)
        if record is None:
            failures.append(BulkFailure(kind=item.kind, id=item.id, reason="Record not found"))
            continue
        if membership.role not in _ROLE_GATES[item.kind]:
            failures.append(
                BulkFailure(kind=item.kind, id=item.id, reason="Role cannot modify this record")
            )
            continue

        if payload.operation == "delete":
            reason = _delete_guard(item.kind, record)
            if reason:
                failures.append(BulkFailure(kind=item.kind, id=item.id, reason=reason))
                continue
            await _apply_delete(item.kind, record, user, db)
            succeeded += 1
        elif payload.operation == "duplicate":
            duplicate = _DUPLICATORS[item.kind](record, user.id)
            db.add(duplicate)
            await db.flush()
            if item.kind == "fuel":
                await fuel_routes._recalculate_consumption(record.vehicle_id, db)
            succeeded += 1
        elif payload.operation == "move":
            reason = _move_guard(item.kind, record)
            if reason:
                failures.append(BulkFailure(kind=item.kind, id=item.id, reason=reason))
                continue
            assert target_vehicle is not None
            record.vehicle_id = target_vehicle.id
            succeeded += 1
        else:  # edit
            reason = _edit_item_guard(item.kind, record, changes)
            if reason:
                failures.append(BulkFailure(kind=item.kind, id=item.id, reason=reason))
                continue
            for field, value in changes.items():
                setattr(record, field, value)
            succeeded += 1

    await db.commit()
    return BulkOperationResult(requested=len(payload.items), succeeded=succeeded, failures=failures)
