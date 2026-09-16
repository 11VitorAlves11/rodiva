"""Odometer history with deterministic recalculation (spec §7)."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.db.filters import active, mark_deleted
from app.models import OdometerReading, Role, Vehicle
from app.schemas.odometer import OdometerReadingIn, OdometerReadingOut, OdometerReadingUpdate
from app.services import audit

router = APIRouter(prefix="/vehicles/{vehicle_id}/odometer-readings", tags=["odometer"])

_CAN_WRITE_RECORDS = {Role.OWNER, Role.MANAGER, Role.EDITOR}


async def _vehicle_in_household(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: AsyncSession
) -> Vehicle:
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.household_id != membership.household_id or vehicle.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


async def _recalculate(vehicle_id: uuid.UUID, db: AsyncSession) -> list[OdometerReading]:
    """Rebuild deltas in date/id order after every write.

    The UUID is generated before insertion and makes readings entered on the same
    date deterministic too. An adjustment begins a new baseline, so it has no
    distance itself; later readings use that adjusted value as their baseline.
    """
    result = await db.scalars(
        select(OdometerReading)
        .where(OdometerReading.vehicle_id == vehicle_id, active(OdometerReading))
        .order_by(OdometerReading.recorded_on, OdometerReading.id)
        .with_for_update()
    )
    readings = list(result)
    previous: OdometerReading | None = None
    for item in readings:
        if previous is not None and item.reading < previous.reading and not item.is_adjustment:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Odometer reading cannot be lower than the preceding reading "
                    "without an adjustment"
                ),
            )
        item.distance = (
            item.reading - previous.reading
            if previous is not None and item.reading >= previous.reading
            else None
        )
        previous = item
    # Mounted equipment derives its distance from the same canonical readings.
    from app.api.routes.equipment import recalculate_equipment_distance

    await recalculate_equipment_distance(vehicle_id, db)
    return readings


@router.get("", response_model=list[OdometerReadingOut])
async def list_readings(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[OdometerReading]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(OdometerReading)
        .where(OdometerReading.vehicle_id == vehicle_id, active(OdometerReading))
        .order_by(OdometerReading.recorded_on.desc(), OdometerReading.id.desc())
    )
    return list(result)


@router.post("", response_model=OdometerReadingOut, status_code=status.HTTP_201_CREATED)
async def create_reading(
    vehicle_id: uuid.UUID,
    payload: OdometerReadingIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> OdometerReading:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    reading = OdometerReading(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(reading)
    await db.flush()
    await _recalculate(vehicle_id, db)
    await db.commit()
    await db.refresh(reading)
    return reading


async def _reading_in_vehicle(
    vehicle_id: uuid.UUID, reading_id: uuid.UUID, db: AsyncSession
) -> OdometerReading:
    reading = await db.get(OdometerReading, reading_id)
    if reading is None or reading.vehicle_id != vehicle_id or reading.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Odometer reading not found"
        )
    return reading


@router.patch("/{reading_id}", response_model=OdometerReadingOut)
async def update_reading(
    vehicle_id: uuid.UUID,
    reading_id: uuid.UUID,
    payload: OdometerReadingUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> OdometerReading:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update records"
        )
    reading = await _reading_in_vehicle(vehicle_id, reading_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reading, field, value)
    if reading.start_reading is not None and reading.start_reading > reading.reading:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Start reading cannot exceed the final reading",
        )
    await _recalculate(vehicle_id, db)
    await db.commit()
    await db.refresh(reading)
    return reading


@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading(
    vehicle_id: uuid.UUID,
    reading_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot delete records"
        )
    reading = await _reading_in_vehicle(vehicle_id, reading_id, db)
    mark_deleted(reading, user.id)
    audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_DELETED,
        entity_type="odometer_reading",
        entity_id=reading.id,
        vehicle_id=vehicle_id,
        summary=f"{reading.reading} on {reading.recorded_on}",
    )
    await db.flush()
    await _recalculate(vehicle_id, db)
    await db.commit()
