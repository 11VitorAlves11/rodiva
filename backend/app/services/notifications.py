"""Turning reminders into notifications, and getting them to members (spec §19).

Evaluation is deliberately separate from the request that changes a reminder:
nothing here runs inside a write, so a notification that cannot be produced or
delivered can never fail the operation that caused it (RF-NOT-008).
"""

import logging
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.filters import active
from app.models import (
    Membership,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    OdometerReading,
    Reminder,
    User,
    Vehicle,
)
from app.services.events import emit
from app.services.events import flush as flush_webhooks
from app.services.urgency import at_least_as_urgent_as, urgency_of

logger = logging.getLogger(__name__)

INAPP = "inapp"
EMAIL = "email"


@dataclass
class EvaluationResult:
    created: int
    delivered: int
    failed: int


async def preference_for(
    user_id: uuid.UUID, household_id: uuid.UUID, db: AsyncSession
) -> NotificationPreference:
    """A member's settings, created with the defaults the first time they are needed."""
    existing = await db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.household_id == household_id,
        )
    )
    if existing is not None:
        return existing
    preference = NotificationPreference(user_id=user_id, household_id=household_id)
    db.add(preference)
    await db.flush()
    return preference


def _in_quiet_hours(preference: NotificationPreference, timezone_name: str, now: datetime) -> bool:
    start, end = preference.quiet_hours_start, preference.quiet_hours_end
    if start is None or end is None or start == end:
        return False
    try:
        local_hour = now.astimezone(ZoneInfo(timezone_name)).hour
    except (ZoneInfoNotFoundError, ValueError):
        local_hour = now.astimezone(UTC).hour
    # A window that wraps past midnight (22 to 7) covers both ends of the day.
    if start < end:
        return start <= local_hour < end
    return local_hour >= start or local_hour < end


async def evaluate_household(household_id: uuid.UUID, db: AsyncSession) -> int:
    """Create notifications for reminders that have become pressing enough.

    Returns how many were newly created. Running twice in a row creates nothing
    the second time: the dedup key carries the urgency, so only a change in how
    pressing a reminder is produces another one.
    """
    vehicles = list(
        await db.scalars(
            select(Vehicle).where(Vehicle.household_id == household_id, active(Vehicle))
        )
    )
    if not vehicles:
        return 0

    members = list(
        await db.scalars(select(Membership).where(Membership.household_id == household_id))
    )
    preferences = {
        member.user_id: await preference_for(member.user_id, household_id, db) for member in members
    }

    created = 0
    for vehicle in vehicles:
        current_odometer = (
            await db.scalar(
                select(func.max(OdometerReading.reading)).where(
                    OdometerReading.vehicle_id == vehicle.id, active(OdometerReading)
                )
            )
            or 0
        )
        reminders = await db.scalars(
            select(Reminder).where(
                Reminder.vehicle_id == vehicle.id,
                Reminder.status != "completed",
                active(Reminder),
            )
        )
        for reminder in reminders:
            urgency = urgency_of(reminder, current_odometer)
            for member in members:
                preference = preferences[member.user_id]
                allowed = not preference.vehicle_ids or str(vehicle.id) in preference.vehicle_ids
                if not allowed or not at_least_as_urgent_as(urgency, preference.min_urgency):
                    continue
                created += await _queue(
                    db,
                    household_id=household_id,
                    user_id=member.user_id,
                    preference=preference,
                    reminder=reminder,
                    vehicle=vehicle,
                    urgency=urgency,
                )
    return created


async def _queue(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    user_id: uuid.UUID,
    preference: NotificationPreference,
    reminder: Reminder,
    vehicle: Vehicle,
    urgency: str,
) -> int:
    """Insert one notification unless the member already has it."""
    dedup_key = f"reminder:{reminder.id}:{urgency}"
    statement = (
        insert(Notification)
        .values(
            household_id=household_id,
            user_id=user_id,
            kind="reminder_due",
            title=reminder.title,
            body=reminder.notes or "",
            context={"urgency": urgency, "vehicle_name": vehicle.name},
            entity_type="reminder",
            entity_id=reminder.id,
            vehicle_id=vehicle.id,
            dedup_key=dedup_key,
        )
        .on_conflict_do_nothing(constraint="uq_notification_dedup")
        .returning(Notification.id)
    )
    notification_id = await db.scalar(statement)
    if notification_id is None:
        return 0
    await emit(
        db,
        household_id=household_id,
        resource="reminder",
        action="due",
        entity_id=reminder.id,
        vehicle_id=vehicle.id,
        data={"title": reminder.title, "urgency": urgency, "vehicle_name": vehicle.name},
    )
    channels = [INAPP] if preference.channel_inapp else []
    if preference.channel_email:
        channels.append(EMAIL)
    for channel in channels:
        db.add(
            NotificationDelivery(
                notification_id=notification_id,
                channel=channel,
                # In-app needs no sending: the row exists, so it is delivered.
                status="sent" if channel == INAPP else "pending",
                sent_at=datetime.now(UTC) if channel == INAPP else None,
            )
        )
    return 1


def _compose(settings: Settings, user: User, notification: Notification) -> EmailMessage:
    context = notification.context or {}
    vehicle = context.get("vehicle_name", "")
    portuguese = (user.locale or "pt-PT").startswith("pt")
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = user.email
    link = f"{settings.public_frontend_url.rstrip('/')}/reminders"
    if portuguese:
        message["Subject"] = f"Rodiva — {vehicle}: {notification.title}"
        message.set_content(
            f"{notification.title}\n{vehicle}\n\n"
            f"{notification.body}\n\nVer na Rodiva: {link}".strip()
        )
    else:
        message["Subject"] = f"Rodiva — {vehicle}: {notification.title}"
        message.set_content(
            f"{notification.title}\n{vehicle}\n\n"
            f"{notification.body}\n\nOpen in Rodiva: {link}".strip()
        )
    return message


def _send(settings: Settings, message: EmailMessage) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_starttls:
            server.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)


async def deliver_pending(db: AsyncSession, limit: int = 100) -> tuple[int, int]:
    """Send what is waiting on a channel that needs sending. Never raises.

    A delivery left pending — SMTP not configured, or the member is inside
    their quiet hours — is picked up by a later run rather than dropped.
    """
    settings = get_settings()
    rows = list(
        await db.scalars(
            select(NotificationDelivery)
            .where(NotificationDelivery.status == "pending")
            .order_by(NotificationDelivery.created_at)
            .limit(limit)
        )
    )
    delivered = failed = 0
    now = datetime.now(UTC)
    for delivery in rows:
        if delivery.channel != EMAIL:
            continue
        if not settings.smtp_host or not settings.smtp_from:
            continue  # Unconfigured, not failed: leave it pending.
        notification = await db.get(Notification, delivery.notification_id)
        if notification is None:
            continue
        user = await db.get(User, notification.user_id)
        if user is None:
            continue
        preference = await preference_for(user.id, notification.household_id, db)
        if _in_quiet_hours(preference, user.timezone or "UTC", now):
            continue
        delivery.attempts += 1
        try:
            _send(settings, _compose(settings, user, notification))
        except (OSError, smtplib.SMTPException) as error:
            # Never name the address or anything else identifying in a log.
            delivery.last_error = type(error).__name__[:500]
            if delivery.attempts >= 5:
                delivery.status = "failed"
            failed += 1
            logger.warning("Notification email could not be delivered")
        else:
            delivery.status = "sent"
            delivery.sent_at = datetime.now(UTC)
            delivery.last_error = ""
            delivered += 1
    return delivered, failed


async def run_once(db: AsyncSession) -> EvaluationResult:
    """Evaluate every household, then flush the delivery queue."""
    household_ids = list(await db.scalars(select(Membership.household_id).distinct()))
    created = 0
    for household_id in household_ids:
        try:
            created += await evaluate_household(household_id, db)
        except Exception:  # noqa: BLE001 - one bad household must not stop the rest
            logger.exception("Notification evaluation failed for a household")
    await db.commit()
    delivered, failed = await deliver_pending(db)
    await db.commit()
    hook_delivered, hook_failed = await flush_webhooks(db)
    await db.commit()
    return EvaluationResult(
        created=created,
        delivered=delivered + hook_delivered,
        failed=failed + hook_failed,
    )
