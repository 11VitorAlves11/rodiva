import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.api.routes.reminders import _current_odometer, _out
from app.db.filters import active
from app.models import Equipment, MountPeriod, OdometerReading, Reminder, Role, TireRotation
from app.schemas.equipment import (
    EquipmentIn,
    EquipmentOut,
    EquipmentUpdate,
    MountIn,
    MountPeriodOut,
    RotationIn,
    RotationOut,
)
from app.schemas.reminders import ReminderIn, ReminderOut
from app.services.google_calendar import sync_reminder

router = APIRouter(prefix="/vehicles/{vehicle_id}/equipment", tags=["equipment"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


def _require_write(membership: CurrentMembership) -> None:
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot modify equipment"
        )


async def _equipment_in_vehicle(
    vehicle_id: uuid.UUID, equipment_id: uuid.UUID, db: DbSession
) -> Equipment:
    item = await db.get(Equipment, equipment_id)
    if item is None or item.vehicle_id != vehicle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return item


async def _open_reminders_counts(
    equipment_ids: list[uuid.UUID], db: DbSession
) -> dict[uuid.UUID, int]:
    if not equipment_ids:
        return {}
    rows = await db.execute(
        select(Reminder.equipment_id, func.count())
        .where(
            Reminder.equipment_id.in_(equipment_ids), active(Reminder), Reminder.status == "active"
        )
        .group_by(Reminder.equipment_id)
    )
    return {equipment_id: count for equipment_id, count in rows.all() if equipment_id is not None}


def _equipment_out(item: Equipment, open_reminders_count: int) -> EquipmentOut:
    return EquipmentOut.model_validate(
        {column.name: getattr(item, column.name) for column in item.__table__.columns}
        | {"open_reminders_count": open_reminders_count}
    )


async def recalculate_equipment_distance(vehicle_id: uuid.UUID, db: DbSession) -> None:
    current = await db.scalar(
        select(func.max(OdometerReading.reading)).where(
            OdometerReading.vehicle_id == vehicle_id, active(OdometerReading)
        )
    )
    items = list(await db.scalars(select(Equipment).where(Equipment.vehicle_id == vehicle_id)))
    for item in items:
        periods = list(
            await db.scalars(select(MountPeriod).where(MountPeriod.equipment_id == item.id))
        )
        total = 0
        for period in periods:
            end = period.unmounted_odometer if period.unmounted_odometer is not None else current
            period.distance = max((end or period.mounted_odometer) - period.mounted_odometer, 0)
            total += period.distance
        item.distance_accumulated = total


@router.get("", response_model=list[EquipmentOut])
async def list_equipment(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[EquipmentOut]:
    await _vehicle_in_household(vehicle_id, membership, db)
    await recalculate_equipment_distance(vehicle_id, db)
    result = await db.scalars(
        select(Equipment).where(Equipment.vehicle_id == vehicle_id).order_by(Equipment.name)
    )
    items = list(result)
    counts = await _open_reminders_counts([item.id for item in items], db)
    return [_equipment_out(item, counts.get(item.id, 0)) for item in items]


@router.post("", response_model=EquipmentOut, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    vehicle_id: uuid.UUID,
    payload: EquipmentIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> EquipmentOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = Equipment(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _equipment_out(item, 0)


@router.patch("/{equipment_id}", response_model=EquipmentOut)
async def update_equipment(
    vehicle_id: uuid.UUID,
    equipment_id: uuid.UUID,
    payload: EquipmentUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> EquipmentOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if item.status == "mounted" and "status" in changes:
        raise HTTPException(status_code=409, detail="Unmount equipment before changing its status")
    for field, value in changes.items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    counts = await _open_reminders_counts([item.id], db)
    return _equipment_out(item, counts.get(item.id, 0))


@router.post("/{equipment_id}/mount", response_model=MountPeriodOut, status_code=201)
async def mount_equipment(
    vehicle_id: uuid.UUID,
    equipment_id: uuid.UUID,
    payload: MountIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> MountPeriod:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    if item.status == "mounted" or item.status in {"sold", "discarded"}:
        raise HTTPException(status_code=409, detail="Equipment cannot be mounted")
    period = MountPeriod(
        equipment_id=item.id,
        mounted_on=payload.on,
        mounted_odometer=payload.odometer,
        positions=payload.positions,
        created_by=user.id,
    )
    item.status = "mounted"
    item.positions = payload.positions
    db.add(period)
    await recalculate_equipment_distance(vehicle_id, db)
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/{equipment_id}/unmount", response_model=MountPeriodOut)
async def unmount_equipment(
    vehicle_id: uuid.UUID,
    equipment_id: uuid.UUID,
    payload: MountIn,
    membership: CurrentMembership,
    db: DbSession,
) -> MountPeriod:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    period = await db.scalar(
        select(MountPeriod)
        .where(MountPeriod.equipment_id == item.id, MountPeriod.unmounted_on.is_(None))
        .with_for_update()
    )
    if (
        period is None
        or payload.on < period.mounted_on
        or payload.odometer < period.mounted_odometer
    ):
        raise HTTPException(status_code=409, detail="Invalid unmount event")
    period.unmounted_on = payload.on
    period.unmounted_odometer = payload.odometer
    item.status = "unmounted"
    item.positions = None
    await recalculate_equipment_distance(vehicle_id, db)
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/{equipment_id}/rotate", response_model=RotationOut, status_code=201)
async def rotate_tires(
    vehicle_id: uuid.UUID,
    equipment_id: uuid.UUID,
    payload: RotationIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> TireRotation:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    if item.kind != "tires" or item.status != "mounted":
        raise HTTPException(status_code=409, detail="Only mounted tires can be rotated")
    rotation = TireRotation(
        equipment_id=item.id,
        rotated_on=payload.on,
        odometer=payload.odometer,
        positions=payload.positions,
        created_by=user.id,
    )
    item.positions = payload.positions
    db.add(rotation)
    await db.commit()
    await db.refresh(rotation)
    return rotation


@router.get("/{equipment_id}/mounts", response_model=list[MountPeriodOut])
async def mount_history(
    vehicle_id: uuid.UUID, equipment_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[MountPeriod]:
    await _vehicle_in_household(vehicle_id, membership, db)
    await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    return list(
        await db.scalars(
            select(MountPeriod)
            .where(MountPeriod.equipment_id == equipment_id)
            .order_by(MountPeriod.mounted_on.desc())
        )
    )


@router.get("/{equipment_id}/rotations", response_model=list[RotationOut])
async def rotation_history(
    vehicle_id: uuid.UUID, equipment_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[TireRotation]:
    await _vehicle_in_household(vehicle_id, membership, db)
    await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    return list(
        await db.scalars(
            select(TireRotation)
            .where(TireRotation.equipment_id == equipment_id)
            .order_by(TireRotation.rotated_on.desc())
        )
    )


@router.get("/{equipment_id}/reminders", response_model=list[ReminderOut])
async def list_equipment_reminders(
    vehicle_id: uuid.UUID, equipment_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[ReminderOut]:
    await _vehicle_in_household(vehicle_id, membership, db)
    await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    current = await _current_odometer(vehicle_id, db)
    result = await db.scalars(
        select(Reminder)
        .where(Reminder.equipment_id == equipment_id, active(Reminder))
        .order_by(Reminder.created_at.desc())
    )
    return [_out(item, current) for item in result]


@router.post(
    "/{equipment_id}/reminders", response_model=ReminderOut, status_code=status.HTTP_201_CREATED
)
async def create_equipment_reminder(
    vehicle_id: uuid.UUID,
    equipment_id: uuid.UUID,
    payload: ReminderIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ReminderOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    reminder = Reminder(
        vehicle_id=item.vehicle_id, equipment_id=item.id, created_by=user.id, **payload.model_dump()
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    background_tasks.add_task(sync_reminder, reminder.id)
    current = await _current_odometer(item.vehicle_id, db)
    return _out(reminder, current)


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    vehicle_id: uuid.UUID,
    equipment_id: uuid.UUID,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = await _equipment_in_vehicle(vehicle_id, equipment_id, db)
    if item.status == "mounted":
        raise HTTPException(status_code=409, detail="Mounted equipment cannot be deleted")
    await db.delete(item)
    await db.commit()
