import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _recalculate, _vehicle_in_household
from app.db.filters import active, mark_deleted
from app.models import (
    InventoryItem,
    OdometerReading,
    Role,
    StockMovement,
    WorkRecord,
    WorkRecordItem,
)
from app.schemas.work_records import (
    COST_TOLERANCE,
    WorkRecordIn,
    WorkRecordItemIn,
    WorkRecordOut,
    WorkRecordUpdate,
)
from app.services import audit

router = APIRouter(prefix="/vehicles/{vehicle_id}/work-records", tags=["work records"])
_CAN_WRITE_RECORDS = {Role.OWNER, Role.MANAGER, Role.EDITOR}


def _check_cost_breakdown(
    total: Decimal | None,
    labour: Decimal | None,
    parts: Decimal | None,
    tax: Decimal | None,
    discount: Decimal | None,
) -> None:
    """The parts must add up to the total, within rounding (RF-INT-009).

    Only checked when a total and at least one component are both given: an
    invoice that only ever showed one number is not wrong for saying so.
    """
    components = [value for value in (labour, parts, tax) if value is not None]
    if total is None or not components:
        return
    summed = sum(components, Decimal("0")) - (discount or Decimal("0"))
    if abs(summed - total) > COST_TOLERANCE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"The cost breakdown adds up to {summed}, not the total of {total}",
        )


def _replace_items(record: WorkRecord, items: list[WorkRecordItemIn]) -> None:
    """Make the record's lines exactly `items`, in the order they were sent.

    Assigning the collection rather than issuing a DELETE: a bulk delete goes
    around the session, leaving the loaded record still holding the old lines,
    and delete-orphan would put them back on the next flush.
    """
    record.items = [
        WorkRecordItem(
            description=item.description,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            position=position,
        )
        for position, item in enumerate(items)
    ]


async def _loaded(record_id: uuid.UUID, db: DbSession) -> WorkRecord:
    """Re-read a record with its lines attached, ordered as the member set them."""
    record = await db.scalar(
        select(WorkRecord).where(WorkRecord.id == record_id).options(selectinload(WorkRecord.items))
    )
    assert record is not None
    return record


@router.get("", response_model=list[WorkRecordOut])
async def list_work_records(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[WorkRecord]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(WorkRecord)
        .where(WorkRecord.vehicle_id == vehicle_id, active(WorkRecord))
        .options(selectinload(WorkRecord.items))
        .order_by(WorkRecord.recorded_on.desc(), WorkRecord.id.desc())
    )
    return list(result)


@router.post("", response_model=WorkRecordOut, status_code=status.HTTP_201_CREATED)
async def create_work_record(
    vehicle_id: uuid.UUID,
    payload: WorkRecordIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> WorkRecord:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    _check_cost_breakdown(
        payload.total_cost,
        payload.labour_cost,
        payload.parts_cost,
        payload.tax_cost,
        payload.discount,
    )
    fields = payload.model_dump(exclude={"items"})
    record = WorkRecord(vehicle_id=vehicle_id, created_by=user.id, **fields)
    _replace_items(record, payload.items)
    db.add(record)
    if payload.odometer_reading is not None:
        db.add(
            OdometerReading(
                vehicle_id=vehicle_id,
                created_by=user.id,
                recorded_on=payload.recorded_on,
                reading=payload.odometer_reading,
                notes="Leitura criada automaticamente a partir de uma intervenção",
            )
        )
    await db.flush()
    await _recalculate(vehicle_id, db)
    await db.commit()
    return await _loaded(record.id, db)


async def _work_record_in_vehicle(
    vehicle_id: uuid.UUID, record_id: uuid.UUID, db: DbSession
) -> WorkRecord:
    record = await db.get(WorkRecord, record_id)
    if record is None or record.vehicle_id != vehicle_id or record.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work record not found")
    return record


@router.patch("/{record_id}", response_model=WorkRecordOut)
async def update_work_record(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: WorkRecordUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> WorkRecord:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update records"
        )
    record = await _work_record_in_vehicle(vehicle_id, record_id, db)
    changes = payload.model_dump(exclude_unset=True)
    items = changes.pop("items", None)
    _check_cost_breakdown(
        changes.get("total_cost", record.total_cost),
        changes.get("labour_cost", record.labour_cost),
        changes.get("parts_cost", record.parts_cost),
        changes.get("tax_cost", record.tax_cost),
        changes.get("discount", record.discount),
    )
    for field, value in changes.items():
        setattr(record, field, value)
    if items is not None:
        _replace_items(record, [WorkRecordItemIn(**item) for item in items])
    await db.commit()
    return await _loaded(record.id, db)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_record(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot delete records"
        )
    record = await _work_record_in_vehicle(vehicle_id, record_id, db)
    await _restore_requisitioned_stock(record_id, user.id, db)
    mark_deleted(record, user.id)
    await audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_DELETED,
        entity_type="work_record",
        entity_id=record.id,
        vehicle_id=vehicle_id,
        summary=record.description,
    )
    await db.commit()


async def _restore_requisitioned_stock(
    record_id: uuid.UUID, user_id: uuid.UUID, db: DbSession
) -> None:
    movements = list(
        await db.scalars(
            select(StockMovement).where(
                StockMovement.work_record_id == record_id, StockMovement.quantity_delta < 0
            )
        )
    )
    for movement in movements:
        item = await db.scalar(
            select(InventoryItem).where(InventoryItem.id == movement.item_id).with_for_update()
        )
        if item is None:
            continue
        restored = -movement.quantity_delta
        item.quantity += restored
        db.add(
            StockMovement(
                item_id=item.id,
                kind="return",
                quantity_delta=restored,
                quantity_after=item.quantity,
                notes="Stock restored after deleting the work record that requisitioned it",
                created_by=user_id,
            )
        )
