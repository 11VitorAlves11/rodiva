"""Fuel fill-ups and deterministic full-to-full consumption calculations."""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _recalculate, _vehicle_in_household
from app.models import FuelRecord, OdometerReading, Role
from app.schemas.fuel import FuelRecordIn, FuelRecordOut

router = APIRouter(prefix="/vehicles/{vehicle_id}/fuel-records", tags=["fuel"])

_CAN_WRITE_RECORDS = {Role.OWNER, Role.MANAGER, Role.EDITOR}


async def _recalculate_consumption(vehicle_id: uuid.UUID, db: AsyncSession) -> list[FuelRecord]:
    result = await db.scalars(
        select(FuelRecord)
        .where(FuelRecord.vehicle_id == vehicle_id)
        .order_by(FuelRecord.recorded_on, FuelRecord.id)
        .with_for_update()
    )
    records = list(result)
    last_full_index: int | None = None
    for index, record in enumerate(records):
        record.consumption_l_per_100km = None
        if record.excluded_from_consumption or not record.full_tank:
            continue
        if last_full_index is not None:
            previous = records[last_full_index]
            if previous.odometer_reading is not None and record.odometer_reading is not None:
                distance = record.odometer_reading - previous.odometer_reading
                if distance > 0:
                    volume = sum(
                        (
                            item.volume_litres
                            for item in records[last_full_index + 1 : index + 1]
                            if not item.excluded_from_consumption
                        ),
                        Decimal("0"),
                    )
                    record.consumption_l_per_100km = (volume * 100 / distance).quantize(
                        Decimal("0.001"), rounding=ROUND_HALF_UP
                    )
        last_full_index = index
    return records


@router.get("", response_model=list[FuelRecordOut])
async def list_fuel_records(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[FuelRecord]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(FuelRecord)
        .where(FuelRecord.vehicle_id == vehicle_id)
        .order_by(FuelRecord.recorded_on.desc(), FuelRecord.id.desc())
    )
    return list(result)


@router.post("", response_model=FuelRecordOut, status_code=status.HTTP_201_CREATED)
async def create_fuel_record(
    vehicle_id: uuid.UUID,
    payload: FuelRecordIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> FuelRecord:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    record = FuelRecord(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(record)
    if payload.odometer_reading is not None:
        db.add(
            OdometerReading(
                vehicle_id=vehicle_id,
                created_by=user.id,
                recorded_on=payload.recorded_on,
                reading=payload.odometer_reading,
                notes="Leitura criada automaticamente a partir de um abastecimento",
            )
        )
    await db.flush()
    await _recalculate(vehicle_id, db)
    await _recalculate_consumption(vehicle_id, db)
    await db.commit()
    await db.refresh(record)
    return record
