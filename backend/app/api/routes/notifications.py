import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select, update

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.models import Notification, Role
from app.schemas.notifications import (
    EvaluationOut,
    NotificationPage,
    PreferenceIn,
    PreferenceOut,
)
from app.services import events
from app.services import notifications as service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationPage)
async def list_notifications(
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
) -> NotificationPage:
    """The caller's own inbox. Notifications are per member, never shared."""
    query = select(Notification).where(
        Notification.user_id == user.id,
        Notification.household_id == membership.household_id,
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    items = list(await db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)))
    unread = (
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.household_id == membership.household_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )
    return NotificationPage(items=items, unread=unread)  # type: ignore[arg-type]


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(notification_id: uuid.UUID, user: CurrentUser, db: DbSession) -> None:
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        await db.commit()


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(user: CurrentUser, membership: CurrentMembership, db: DbSession) -> None:
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.household_id == membership.household_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    await db.commit()


@router.get("/preferences", response_model=PreferenceOut)
async def read_preferences(
    user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> PreferenceOut:
    preference = await service.preference_for(user.id, membership.household_id, db)
    await db.commit()
    return PreferenceOut.model_validate(preference)


@router.put("/preferences", response_model=PreferenceOut)
async def write_preferences(
    payload: PreferenceIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> PreferenceOut:
    preference = await service.preference_for(user.id, membership.household_id, db)
    preference.channel_inapp = payload.channel_inapp
    preference.channel_email = payload.channel_email
    preference.min_urgency = payload.min_urgency
    preference.vehicle_ids = [str(item) for item in payload.vehicle_ids]
    preference.quiet_hours_start = payload.quiet_hours_start
    preference.quiet_hours_end = payload.quiet_hours_end
    await db.commit()
    await db.refresh(preference)
    return PreferenceOut.model_validate(preference)


@router.post("/run", response_model=EvaluationOut)
async def run_evaluation(membership: CurrentMembership, db: DbSession) -> EvaluationOut:
    """Evaluate this household now, rather than waiting for the scheduled run.

    The background schedule covers the normal case (RF-NOT-005); this is for an
    operator who wants it now, or an external scheduler driving it instead.
    """
    if membership.role != Role.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can run the evaluation"
        )
    created = await service.evaluate_household(membership.household_id, db)
    await db.commit()
    delivered, failed = await service.deliver_pending(db)
    await db.commit()
    # The same run flushes the outbox, so an event queued just now goes out too.
    hook_delivered, hook_failed = await events.flush(db)
    await db.commit()
    return EvaluationOut(
        created=created,
        delivered=delivered + hook_delivered,
        failed=failed + hook_failed,
    )
