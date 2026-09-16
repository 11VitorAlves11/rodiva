import csv
import io
import re
import uuid
import zipfile
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path, PurePosixPath
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentMembership, DbSession
from app.models import (
    Attachment,
    ChargingRecord,
    ExpenseRecord,
    FuelRecord,
    InventoryItem,
    OdometerReading,
    Reminder,
    Vehicle,
    WorkRecord,
)
from app.schemas.reports import CategoryTotal, MonthlyTotal, ReportSummary, VehicleReport

router = APIRouter(prefix="/reports", tags=["reports"])


async def _vehicles(
    membership: CurrentMembership, db: DbSession, requested: list[uuid.UUID]
) -> list[Vehicle]:
    query = select(Vehicle).where(
        Vehicle.household_id == membership.household_id, Vehicle.deleted_at.is_(None)
    )
    if requested:
        query = query.where(Vehicle.id.in_(requested))
    items = list(await db.scalars(query.order_by(Vehicle.name)))
    if requested and len({item.id for item in items}) != len(set(requested)):
        raise HTTPException(status_code=404, detail="One or more vehicles were not found")
    return items


def _date_filter(query: Any, column: Any, date_from: date | None, date_to: date | None) -> Any:
    if date_from:
        query = query.where(column >= date_from)
    if date_to:
        query = query.where(column <= date_to)
    return query


_UNSAFE_SEGMENT_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_segment(value: str, fallback: str) -> str:
    cleaned = _UNSAFE_SEGMENT_CHARS.sub("_", value).strip("._")
    return cleaned or fallback


def _dedupe_entry_name(name: str, seen: set[str], unique_suffix: str) -> str:
    if name not in seen:
        return name
    path = PurePosixPath(name)
    candidate = f"{path.parent}/{path.stem}-{unique_suffix}{path.suffix}"
    while candidate in seen:
        unique_suffix = uuid.uuid4().hex[:6]
        candidate = f"{path.parent}/{path.stem}-{unique_suffix}{path.suffix}"
    return candidate


@router.get("/summary", response_model=ReportSummary)
async def report_summary(
    membership: CurrentMembership,
    db: DbSession,
    vehicle_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ReportSummary:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    selected = await _vehicles(membership, db, vehicle_id or [])
    selected_ids = [item.id for item in selected]
    if not selected_ids:
        return ReportSummary(
            date_from=date_from,
            date_to=date_to,
            currency="EUR",
            total_cost=Decimal(0),
            total_distance=0,
            inventory_value=Decimal(0),
            overdue_reminders=0,
            vehicles=[],
        )

    charging_items = list(
        await db.scalars(
            _date_filter(
                select(ChargingRecord).where(ChargingRecord.vehicle_id.in_(selected_ids)),
                ChargingRecord.recorded_on,
                date_from,
                date_to,
            )
        )
    )
    fuel_query = select(FuelRecord).where(FuelRecord.vehicle_id.in_(selected_ids))
    work_query = select(WorkRecord).where(WorkRecord.vehicle_id.in_(selected_ids))
    expense_query = select(ExpenseRecord).where(
        ExpenseRecord.vehicle_id.in_(selected_ids), ExpenseRecord.status == "paid"
    )
    odometer_query = select(OdometerReading).where(OdometerReading.vehicle_id.in_(selected_ids))
    fuel_items = list(
        await db.scalars(_date_filter(fuel_query, FuelRecord.recorded_on, date_from, date_to))
    )
    work_items = list(
        await db.scalars(_date_filter(work_query, WorkRecord.recorded_on, date_from, date_to))
    )
    expense_items = list(
        await db.scalars(_date_filter(expense_query, ExpenseRecord.issued_on, date_from, date_to))
    )
    odometer_items = list(
        await db.scalars(
            _date_filter(odometer_query, OdometerReading.recorded_on, date_from, date_to)
        )
    )
    inventory = list(
        await db.scalars(
            select(InventoryItem).where(InventoryItem.household_id == membership.household_id)
        )
    )
    today = date.today()
    overdue = list(
        await db.scalars(
            select(Reminder).where(
                Reminder.vehicle_id.in_(selected_ids),
                Reminder.completed_at.is_(None),
                Reminder.due_date.is_not(None),
                Reminder.due_date < today,
            )
        )
    )

    reports: list[VehicleReport] = []
    for vehicle in selected:
        vehicle_charging = [item for item in charging_items if item.vehicle_id == vehicle.id]
        vehicle_fuel = [item for item in fuel_items if item.vehicle_id == vehicle.id]
        vehicle_work = [item for item in work_items if item.vehicle_id == vehicle.id]
        vehicle_expenses = [item for item in expense_items if item.vehicle_id == vehicle.id]
        vehicle_odometer = [item for item in odometer_items if item.vehicle_id == vehicle.id]
        categories: defaultdict[str, Decimal] = defaultdict(Decimal)
        months: defaultdict[str, dict[str, Decimal | int]] = defaultdict(
            lambda: {
                "fuel": Decimal(0),
                "charging": Decimal(0),
                "work": Decimal(0),
                "expenses": Decimal(0),
                "distance": 0,
            }
        )
        for charge in vehicle_charging:
            categories["charging"] += charge.total_cost
            months[charge.recorded_on.strftime("%Y-%m")]["charging"] += charge.total_cost
        for item in vehicle_fuel:
            categories["fuel"] += item.total_price
            months[item.recorded_on.strftime("%Y-%m")]["fuel"] += item.total_price
        for item in vehicle_work:
            amount = item.total_cost or Decimal(0)
            categories[f"work:{item.kind}"] += amount
            months[item.recorded_on.strftime("%Y-%m")]["work"] += amount
        for item in vehicle_expenses:
            categories[f"expense:{item.category}"] += item.amount
            months[item.issued_on.strftime("%Y-%m")]["expenses"] += item.amount
        for item in vehicle_odometer:
            distance = item.distance or 0
            months[item.recorded_on.strftime("%Y-%m")]["distance"] += distance
        total = sum(categories.values(), Decimal(0))
        distance = sum((item.distance or 0) for item in vehicle_odometer)
        consumptions = [
            item.consumption_l_per_100km
            for item in vehicle_fuel
            if item.consumption_l_per_100km is not None
        ]
        reports.append(
            VehicleReport(
                vehicle_id=vehicle.id,
                vehicle_name=vehicle.name,
                distance_unit=vehicle.distance_unit,
                total_cost=total,
                distance=distance,
                cost_per_distance=(total / distance).quantize(
                    Decimal("0.001"), rounding=ROUND_HALF_UP
                )
                if distance
                else None,
                consumption_average=(sum(consumptions, Decimal(0)) / len(consumptions)).quantize(
                    Decimal("0.001"), rounding=ROUND_HALF_UP
                )
                if consumptions
                else None,
                consumption_minimum=min(consumptions) if consumptions else None,
                consumption_maximum=max(consumptions) if consumptions else None,
                categories=[
                    CategoryTotal(category=name, amount=amount)
                    for name, amount in sorted(categories.items())
                ],
                monthly=[
                    MonthlyTotal(
                        month=month,
                        fuel=Decimal(values["fuel"]),
                        charging=Decimal(values["charging"]),
                        work=Decimal(values["work"]),
                        expenses=Decimal(values["expenses"]),
                        total=Decimal(values["fuel"])
                        + Decimal(values["charging"])
                        + Decimal(values["work"])
                        + Decimal(values["expenses"]),
                        distance=int(values["distance"]),
                    )
                    for month, values in sorted(months.items())
                ],
            )
        )
    return ReportSummary(
        date_from=date_from,
        date_to=date_to,
        currency="EUR",
        total_cost=sum((item.total_cost for item in reports), Decimal(0)),
        total_distance=sum(item.distance for item in reports),
        inventory_value=sum(
            (item.quantity * (item.unit_cost or Decimal(0)) for item in inventory), Decimal(0)
        ),
        overdue_reminders=len(overdue),
        vehicles=reports,
    )


@router.get("/export.csv")
async def export_csv(
    membership: CurrentMembership,
    db: DbSession,
    vehicle_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    locale: str = "pt-PT",
) -> Response:
    selected = await _vehicles(membership, db, vehicle_id or [])
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";" if locale.lower().startswith("pt") else ",")
    writer.writerow(
        ["record_type", "vehicle", "date", "category", "description", "amount", "odometer"]
    )
    for vehicle in selected:
        sources = [
            ("charging", ChargingRecord, ChargingRecord.recorded_on, ChargingRecord.vehicle_id),
            ("fuel", FuelRecord, FuelRecord.recorded_on, FuelRecord.vehicle_id),
            ("work", WorkRecord, WorkRecord.recorded_on, WorkRecord.vehicle_id),
            ("expense", ExpenseRecord, ExpenseRecord.issued_on, ExpenseRecord.vehicle_id),
        ]
        for record_type, model, date_column, vehicle_column in sources:
            query = select(model).where(vehicle_column == vehicle.id)
            records = list(await db.scalars(_date_filter(query, date_column, date_from, date_to)))
            for item in records:
                if record_type == "charging":
                    category, description, amount, odometer = (
                        item.charger_type,
                        item.location or "",
                        item.total_cost,
                        item.odometer_reading,
                    )
                elif record_type == "fuel":
                    category, description, amount, odometer = (
                        item.fuel_type or "fuel",
                        item.station or "",
                        item.total_price,
                        item.odometer_reading,
                    )
                elif record_type == "work":
                    category, description, amount, odometer = (
                        item.kind,
                        item.description,
                        item.total_cost or Decimal(0),
                        item.odometer_reading,
                    )
                else:
                    category, description, amount, odometer = (
                        item.category,
                        item.supplier or "",
                        item.amount,
                        "",
                    )
                writer.writerow(
                    [
                        record_type,
                        vehicle.name,
                        getattr(item, "recorded_on", getattr(item, "issued_on", "")),
                        category,
                        description,
                        amount,
                        odometer or "",
                    ]
                )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="rodiva-report.csv"'},
    )


@router.get("/attachments.zip")
async def export_attachments_zip(
    membership: CurrentMembership,
    db: DbSession,
    settings: AppSettings,
    vehicle_id: Annotated[list[uuid.UUID] | None, Query()] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Response:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    selected = await _vehicles(membership, db, vehicle_id or [])

    buffer = io.BytesIO()
    seen_names: set[str] = set()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for vehicle in selected:
            query = select(Attachment).where(Attachment.vehicle_id == vehicle.id)
            query = _date_filter(query, Attachment.created_at, date_from, date_to)
            attachments = list(
                await db.scalars(query.order_by(Attachment.created_at, Attachment.id))
            )
            vehicle_folder = _safe_segment(vehicle.name, "vehicle") + f"_{vehicle.id.hex[:8]}"
            for attachment in attachments:
                file_path = Path(settings.storage_path) / attachment.storage_key
                if not file_path.is_file():
                    continue
                prefix = attachment.created_at.strftime("%Y-%m-%d")
                original_name = _safe_segment(PurePosixPath(attachment.filename).name, "attachment")
                entry_name = _dedupe_entry_name(
                    f"{vehicle_folder}/{prefix}_{original_name}",
                    seen_names,
                    attachment.id.hex[:6],
                )
                seen_names.add(entry_name)
                archive.write(file_path, entry_name)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="rodiva-attachments.zip"'},
    )
