import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.db.filters import active, mark_deleted
from app.models import Role, Vehicle
from app.models.charging_record import ChargingRecord
from app.schemas.charging import ChargingIn, ChargingOut
from app.services import audit

router = APIRouter(prefix="/vehicles/{vehicle_id}/charging-records", tags=["charging"])


async def recalculate(vehicle: Vehicle, db: DbSession) -> None:
    rows = list(
        await db.scalars(
            select(ChargingRecord)
            .where(ChargingRecord.vehicle_id == vehicle.id, active(ChargingRecord))
            .order_by(ChargingRecord.recorded_on, ChargingRecord.created_at, ChargingRecord.id)
        )
    )
    baseline: ChargingRecord | None = None
    energy = Decimal(0)
    previous_reading: int | None = None
    for row in rows:
        row.efficiency_kwh_per_100km = None
        reading = row.odometer_reading
        if reading is not None:
            if previous_reading is not None and reading < previous_reading:
                raise HTTPException(
                    status_code=422, detail="Charging odometer readings must not decrease"
                )
            previous_reading = reading
        if baseline is None:
            if row.soc_end is not None and reading is not None:
                baseline = row
            continue
        energy += row.energy_kwh
        if row.soc_end == baseline.soc_end and reading is not None:
            assert baseline.odometer_reading is not None
            distance = Decimal(reading - baseline.odometer_reading)
            if vehicle.distance_unit == "mi":
                distance *= Decimal("1.609344")
            if distance > 0:
                row.efficiency_kwh_per_100km = (energy * 100 / distance).quantize(
                    Decimal("0.001"), rounding=ROUND_HALF_UP
                )
            baseline = row
            energy = Decimal(0)


@router.get("", response_model=list[ChargingOut])
async def list_charging(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[ChargingRecord]:
    await _vehicle_in_household(vehicle_id, membership, db)
    return list(
        await db.scalars(
            select(ChargingRecord)
            .where(ChargingRecord.vehicle_id == vehicle_id, active(ChargingRecord))
            .order_by(ChargingRecord.recorded_on.desc(), ChargingRecord.created_at.desc())
        )
    )


async def writable(vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession) -> Vehicle:
    vehicle = await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in {Role.OWNER, Role.MANAGER, Role.EDITOR}:
        raise HTTPException(status_code=403, detail="Role cannot change records")
    await db.scalar(
        select(Vehicle).where(Vehicle.id == vehicle_id, active(Vehicle)).with_for_update()
    )
    return vehicle


@router.post("", response_model=ChargingOut, status_code=201)
async def create_charging(
    vehicle_id: uuid.UUID,
    payload: ChargingIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> ChargingRecord:
    vehicle = await writable(vehicle_id, membership, db)
    row = ChargingRecord(
        vehicle_id=vehicle_id,
        created_by=user.id,
        **payload.model_dump(),
        unit_price=(payload.total_cost / payload.energy_kwh).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        ),
    )
    db.add(row)
    await db.flush()
    await recalculate(vehicle, db)
    await db.commit()
    return row


@router.patch("/{record_id}", response_model=ChargingOut)
async def update_charging(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ChargingIn,
    membership: CurrentMembership,
    db: DbSession,
) -> ChargingRecord:
    vehicle = await writable(vehicle_id, membership, db)
    row = await db.get(ChargingRecord, record_id)
    if row is None or row.vehicle_id != vehicle_id or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Charging record not found")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    row.unit_price = (payload.total_cost / payload.energy_kwh).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    await db.flush()
    await recalculate(vehicle, db)
    await db.commit()
    return row


@router.delete("/{record_id}", status_code=204)
async def delete_charging(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    vehicle = await writable(vehicle_id, membership, db)
    row = await db.get(ChargingRecord, record_id)
    if row is None or row.vehicle_id != vehicle_id or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Charging record not found")
    mark_deleted(row, user.id)
    await audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_DELETED,
        entity_type="charging_record",
        entity_id=row.id,
        vehicle_id=vehicle_id,
        summary=f"{row.energy_kwh} kWh on {row.recorded_on}",
    )
    await db.flush()
    await recalculate(vehicle, db)
    await db.commit()
