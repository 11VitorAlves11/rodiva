import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.models import OdometerReading, Reminder, Role
from app.schemas.reminders import ReminderIn, ReminderOut, ReminderUpdate, Urgency
from app.services.google_calendar import (
    pending_deletions_for,
    sync_reminder,
    sync_reminder_deletion,
)

router = APIRouter(prefix="/vehicles/{vehicle_id}/reminders", tags=["reminders"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


def _urgency(reminder: Reminder, current_odometer: int) -> Urgency:
    if reminder.status == "completed":
        return "completed"
    days = (reminder.due_date - date.today()).days if reminder.due_date else None
    distance = reminder.due_odometer - current_odometer if reminder.due_odometer else None
    if (days is not None and days < 0) or (distance is not None and distance <= 0):
        return "overdue"
    if (days is not None and days <= 7) or (distance is not None and distance <= 250):
        return "very_urgent"
    if (days is not None and days <= 30) or (distance is not None and distance <= 1_000):
        return "urgent"
    if (days is not None and days <= 90) or (distance is not None and distance <= 3_000):
        return "upcoming"
    return "future"


def _out(reminder: Reminder, odometer_value: int) -> ReminderOut:
    return ReminderOut.model_validate(
        {column.name: getattr(reminder, column.name) for column in reminder.__table__.columns}
        | {"urgency": _urgency(reminder, odometer_value)}
    )


async def _current_odometer(vehicle_id: uuid.UUID, db: DbSession) -> int:
    return (
        await db.scalar(
            select(func.max(OdometerReading.reading)).where(
                OdometerReading.vehicle_id == vehicle_id
            )
        )
        or 0
    )


async def _reminder_for_vehicle(
    vehicle_id: uuid.UUID, reminder_id: uuid.UUID, db: DbSession
) -> Reminder:
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None or reminder.vehicle_id != vehicle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return reminder


def _require_write_access(membership: CurrentMembership) -> None:
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update records"
        )


@router.get("", response_model=list[ReminderOut])
async def list_reminders(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[ReminderOut]:
    await _vehicle_in_household(vehicle_id, membership, db)
    current = await _current_odometer(vehicle_id, db)
    result = await db.scalars(
        select(Reminder)
        .where(Reminder.vehicle_id == vehicle_id)
        .order_by(Reminder.created_at.desc())
    )
    order = {
        "overdue": 0,
        "very_urgent": 1,
        "urgent": 2,
        "upcoming": 3,
        "future": 4,
        "completed": 5,
    }
    return sorted((_out(item, current) for item in result), key=lambda item: order[item.urgency])


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    vehicle_id: uuid.UUID,
    payload: ReminderIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ReminderOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write_access(membership)
    reminder = Reminder(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    background_tasks.add_task(sync_reminder, reminder.id)
    current = await _current_odometer(vehicle_id, db)
    return _out(reminder, current)


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    vehicle_id: uuid.UUID,
    reminder_id: uuid.UUID,
    payload: ReminderUpdate,
    membership: CurrentMembership,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ReminderOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write_access(membership)
    reminder = await _reminder_for_vehicle(vehicle_id, reminder_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("title") is None and "title" in changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Title cannot be null",
        )

    due_date = changes.get("due_date", reminder.due_date)
    due_odometer = changes.get("due_odometer", reminder.due_odometer)
    if due_date is None and due_odometer is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A reminder needs a due date or odometer value",
        )
    for field, value in changes.items():
        setattr(reminder, field, value)
    await db.commit()
    await db.refresh(reminder)
    background_tasks.add_task(sync_reminder, reminder.id)
    return _out(reminder, await _current_odometer(vehicle_id, db))


@router.post("/{reminder_id}/complete", response_model=ReminderOut)
async def complete_reminder(
    vehicle_id: uuid.UUID,
    reminder_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ReminderOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write_access(membership)
    reminder = await _reminder_for_vehicle(vehicle_id, reminder_id, db)
    reminder.status = "completed"
    reminder.completed_at = datetime.now(UTC)
    renewed: Reminder | None = None

    if reminder.repeat_days or reminder.repeat_distance:
        # RF-LEM-004/005: renew from the actual completion date and reading,
        # not the reminder's original due date.
        current = await _current_odometer(vehicle_id, db)
        renewed = Reminder(
            vehicle_id=vehicle_id,
            equipment_id=reminder.equipment_id,
            created_by=user.id,
            title=reminder.title,
            due_date=date.today() + timedelta(days=reminder.repeat_days)
            if reminder.repeat_days
            else None,
            due_odometer=current + reminder.repeat_distance if reminder.repeat_distance else None,
            repeat_days=reminder.repeat_days,
            repeat_distance=reminder.repeat_distance,
            notes=reminder.notes,
        )
        db.add(renewed)

    await db.commit()
    await db.refresh(reminder)
    background_tasks.add_task(sync_reminder, reminder.id)
    if renewed is not None:
        background_tasks.add_task(sync_reminder, renewed.id)
    return _out(reminder, 0)


@router.post("/{reminder_id}/reopen", response_model=ReminderOut)
async def reopen_reminder(
    vehicle_id: uuid.UUID,
    reminder_id: uuid.UUID,
    membership: CurrentMembership,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ReminderOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write_access(membership)
    reminder = await _reminder_for_vehicle(vehicle_id, reminder_id, db)
    reminder.status = "active"
    reminder.completed_at = None
    await db.commit()
    await db.refresh(reminder)
    background_tasks.add_task(sync_reminder, reminder.id)
    return _out(reminder, await _current_odometer(vehicle_id, db))


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    vehicle_id: uuid.UUID,
    reminder_id: uuid.UUID,
    membership: CurrentMembership,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write_access(membership)
    reminder = await _reminder_for_vehicle(vehicle_id, reminder_id, db)
    # Captured before the delete: calendar_sync_events cascades away with the
    # reminder, so this is the last point anything can still read those rows.
    pending = await pending_deletions_for(reminder_id, db)
    await db.delete(reminder)
    await db.commit()
    background_tasks.add_task(sync_reminder_deletion, pending)
