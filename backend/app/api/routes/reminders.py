import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.models import OdometerReading, Reminder, Role
from app.schemas.reminders import ReminderIn, ReminderOut, Urgency

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


@router.get("", response_model=list[ReminderOut])
async def list_reminders(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[ReminderOut]:
    await _vehicle_in_household(vehicle_id, membership, db)
    current = (
        await db.scalar(
            select(func.max(OdometerReading.reading)).where(
                OdometerReading.vehicle_id == vehicle_id
            )
        )
        or 0
    )
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
) -> ReminderOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    reminder = Reminder(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    current = (
        await db.scalar(
            select(func.max(OdometerReading.reading)).where(
                OdometerReading.vehicle_id == vehicle_id
            )
        )
        or 0
    )
    return _out(reminder, current)


@router.post("/{reminder_id}/complete", response_model=ReminderOut)
async def complete_reminder(
    vehicle_id: uuid.UUID,
    reminder_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> ReminderOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update records"
        )
    reminder = await db.get(Reminder, reminder_id)
    if reminder is None or reminder.vehicle_id != vehicle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    reminder.status = "completed"
    reminder.completed_at = datetime.now(UTC)

    if reminder.repeat_days or reminder.repeat_distance:
        # RF-LEM-004/005: renew from the actual completion date and reading,
        # not the reminder's original due date.
        current = (
            await db.scalar(
                select(func.max(OdometerReading.reading)).where(
                    OdometerReading.vehicle_id == vehicle_id
                )
            )
            or 0
        )
        db.add(
            Reminder(
                vehicle_id=vehicle_id,
                created_by=user.id,
                title=reminder.title,
                due_date=date.today() + timedelta(days=reminder.repeat_days)
                if reminder.repeat_days
                else None,
                due_odometer=current + reminder.repeat_distance
                if reminder.repeat_distance
                else None,
                repeat_days=reminder.repeat_days,
                repeat_distance=reminder.repeat_distance,
                notes=reminder.notes,
            )
        )

    await db.commit()
    await db.refresh(reminder)
    return _out(reminder, 0)
