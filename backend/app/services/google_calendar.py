"""Google Calendar integration (RF-GCAL-001..009).

Unidirectional (Rodiva -> Google) sync of reminders into a member's own Google
Calendar, built against the documented v3 Calendar / OAuth2 REST APIs via
`httpx` rather than Google's official (synchronous) client libraries, to stay
consistent with this project's async stack.

The whole module is a no-op whenever `settings.google_calendar_enabled` is
false (no `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` configured) — that is the
default and shipped state, since no Google Cloud OAuth client exists yet.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.filters import active
from app.db.session import get_sessionmaker
from app.models import (
    CalendarSyncEvent,
    GoogleCalendarConnection,
    OdometerReading,
    Reminder,
    Vehicle,
)
from app.services.token_crypto import decrypt, encrypt

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

# Narrowest scope that lets Rodiva manage only the events it creates, plus
# enough identity to show the connected account's email (RF-GCAL-001).
SCOPES = "https://www.googleapis.com/auth/calendar.events openid email"

# How far ahead of expiry to refresh, so a token about to expire mid-request
# is treated as already expired.
_REFRESH_SKEW = timedelta(minutes=2)


def _callback_redirect_uri() -> str:
    return f"{get_settings().public_base_url}/api/calendar/google/callback"


def build_authorize_url(state: str) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": _callback_redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        # Forces Google to hand back a refresh_token even for a member who
        # connected before and only has a stale one cached server-side.
        "prompt": "consent",
        "state": state,
    }
    return str(httpx.URL(AUTHORIZE_URL, params=params))


async def exchange_code(code: str) -> dict[str, Any]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": _callback_redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload


async def fetch_account_email(access_token: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return str(data.get("email", ""))


async def refresh_access_token(connection: GoogleCalendarConnection, db: AsyncSession) -> str:
    """Return a usable access token, refreshing it first if it has expired (or is close to it)."""
    now = datetime.now(UTC)
    if connection.token_expires_at - now > _REFRESH_SKEW:
        return decrypt(connection.access_token_encrypted)

    settings = get_settings()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "refresh_token": decrypt(connection.refresh_token_encrypted),
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        payload = response.json()

    access_token: str = payload["access_token"]
    connection.access_token_encrypted = encrypt(access_token)
    connection.token_expires_at = now + timedelta(seconds=payload.get("expires_in", 3600))
    await db.commit()
    return access_token


async def list_calendars(access_token: str) -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{CALENDAR_API_BASE}/users/me/calendarList",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        return [{"id": item["id"], "summary": item.get("summary", item["id"])} for item in items]


async def revoke_token(token: str) -> None:
    """Best-effort revoke at Google — failures are swallowed by the caller."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(REVOKE_URL, data={"token": token})
        response.raise_for_status()


# --- Event sync -------------------------------------------------------------

_URGENCY_LABELS: dict[str, str] = {
    "overdue": "Atrasado",
    "very_urgent": "Muito urgente",
    "urgent": "Urgente",
    "upcoming": "A aproximar-se",
    "future": "Futuro",
    "completed": "Concluído",
}


def _urgency(reminder: Reminder, current_odometer: int) -> str:
    # Deliberately duplicated from app.api.routes.reminders._urgency (kept in
    # sync manually): importing that module here would create an import cycle,
    # since routes/reminders.py calls into this service on every mutation.
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


async def _current_odometer(vehicle_id: uuid.UUID, db: AsyncSession) -> int:

    return (
        await db.scalar(
            select(func.max(OdometerReading.reading)).where(
                OdometerReading.vehicle_id == vehicle_id, active(OdometerReading)
            )
        )
        or 0
    )


def _event_body(vehicle: Vehicle, reminder: Reminder, urgency: str) -> dict[str, Any]:
    settings = get_settings()
    assert reminder.due_date is not None
    end = reminder.due_date + timedelta(days=1)
    link = f"{settings.public_frontend_url}/vehicles/{vehicle.id}"
    description_lines = [
        f"Veículo: {vehicle.name}",
        f"Urgência: {_URGENCY_LABELS.get(urgency, urgency)}",
    ]
    if reminder.notes:
        description_lines.append(reminder.notes)
    description_lines.append(f"Abrir na Rodiva: {link}")
    return {
        "summary": f"{vehicle.name} · {reminder.title}",
        "description": "\n".join(description_lines),
        "start": {"date": reminder.due_date.isoformat()},
        "end": {"date": end.isoformat()},
    }


async def _get_sync_event(
    connection_id: uuid.UUID, reminder_id: uuid.UUID, db: AsyncSession
) -> CalendarSyncEvent | None:
    result: CalendarSyncEvent | None = await db.scalar(
        select(CalendarSyncEvent).where(
            CalendarSyncEvent.connection_id == connection_id,
            CalendarSyncEvent.reminder_id == reminder_id,
        )
    )
    return result


async def _delete_remote_event(
    connection: GoogleCalendarConnection, sync_event: CalendarSyncEvent, db: AsyncSession
) -> None:
    """Call the Calendar API delete and remove the bookkeeping row.

    Errors are recorded on the sync event (RF-GCAL-008) and swallowed —
    deletion is inherently best-effort once the local reminder is gone.
    """
    try:
        if sync_event.external_event_id:
            access_token = await refresh_access_token(connection, db)
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.delete(
                    f"{CALENDAR_API_BASE}/calendars/{sync_event.external_calendar_id}"
                    f"/events/{sync_event.external_event_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                # Google returns 410 Gone for an event already deleted remotely —
                # both count as success from Rodiva's point of view.
                if response.status_code not in (200, 204, 410, 404):
                    response.raise_for_status()
        await db.delete(sync_event)
        await db.commit()
    except Exception as error:  # noqa: BLE001 - must never propagate
        logger.warning("Failed to delete Google Calendar event: %s", error)
        sync_event.status = "error"
        sync_event.last_error = str(error)
        connection.last_error = str(error)
        await db.commit()


async def upsert_event(
    connection: GoogleCalendarConnection, reminder: Reminder, vehicle: Vehicle, db: AsyncSession
) -> None:
    """Create or update the Google Calendar event mirroring one reminder.

    RF-GCAL-006: a reminder with no due date (distance-only, no ETA estimator
    exists yet in this codebase) is not synced. If a sync event already
    existed for it (its due_date got cleared after being set), it is deleted
    instead of left stale.
    """
    existing = await _get_sync_event(connection.id, reminder.id, db)

    if reminder.due_date is None:
        if existing is not None:
            existing.status = "pending_delete"
            await db.commit()
            await _delete_remote_event(connection, existing, db)
        return

    if connection.calendar_id is None:
        return

    try:
        access_token = await refresh_access_token(connection, db)
        current_odometer = await _current_odometer(vehicle.id, db)
        urgency = _urgency(reminder, current_odometer)
        body = _event_body(vehicle, reminder, urgency)

        async with httpx.AsyncClient(timeout=10) as client:
            if existing is not None and existing.external_event_id:
                response = await client.patch(
                    f"{CALENDAR_API_BASE}/calendars/{connection.calendar_id}"
                    f"/events/{existing.external_event_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json=body,
                )
            else:
                response = await client.post(
                    f"{CALENDAR_API_BASE}/calendars/{connection.calendar_id}/events",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json=body,
                )
            response.raise_for_status()
            event = response.json()

        if existing is None:
            existing = CalendarSyncEvent(
                connection_id=connection.id,
                reminder_id=reminder.id,
                external_calendar_id=connection.calendar_id,
            )
            db.add(existing)
        existing.external_event_id = event.get("id", existing.external_event_id)
        existing.external_calendar_id = connection.calendar_id
        existing.status = "synced"
        existing.last_synced_at = datetime.now(UTC)
        existing.last_error = None
        connection.last_error = None
        await db.commit()
    except Exception as error:  # noqa: BLE001 - never block reminder management
        logger.warning("Failed to sync reminder %s to Google Calendar: %s", reminder.id, error)
        if existing is None:
            existing = CalendarSyncEvent(
                connection_id=connection.id,
                reminder_id=reminder.id,
                external_calendar_id=connection.calendar_id or "",
            )
            db.add(existing)
        existing.status = "error"
        existing.last_error = str(error)
        connection.last_error = str(error)
        await db.commit()


async def sync_reminder(reminder_id: uuid.UUID) -> None:
    """Entry point routes call (via `BackgroundTasks`) after creating, updating,
    completing or reopening a reminder — never after deleting one, see
    `take_pending_deletions`/`sync_reminder_deletion` below for why deletion needs
    a different shape.

    Opens its own database session rather than reusing the request-scoped one:
    by the time a background task runs (after the response has been sent) the
    request's session dependency has already been torn down. Never raises —
    RF-GCAL-008 requires errors to be visible on the connection/sync-event
    rows, not to disrupt the reminder mutation that triggered this call.
    """
    settings = get_settings()
    if not settings.google_calendar_enabled:
        return

    session_maker = get_sessionmaker()
    async with session_maker() as db:
        try:
            reminder = await db.get(Reminder, reminder_id)
            if reminder is None:
                return
            vehicle = await db.get(Vehicle, reminder.vehicle_id)
            if vehicle is None:
                return

            connections = await db.scalars(
                select(GoogleCalendarConnection).where(
                    GoogleCalendarConnection.household_id == vehicle.household_id,
                    GoogleCalendarConnection.status == "active",
                )
            )
            vehicle_id_str = str(vehicle.id)
            for connection in list(connections):
                if vehicle_id_str not in (connection.synced_vehicle_ids or []):
                    continue
                try:
                    await upsert_event(connection, reminder, vehicle, db)
                except Exception as error:  # noqa: BLE001 - one bad connection must not affect others
                    logger.warning(
                        "Google Calendar sync failed for connection %s: %s", connection.id, error
                    )
                    connection.last_error = str(error)
                    await db.commit()
        except Exception as error:  # noqa: BLE001 - this function must never raise
            logger.warning(
                "Unexpected error syncing reminder %s to Google Calendar: %s", reminder_id, error
            )


@dataclass(frozen=True)
class PendingEventDeletion:
    """A snapshot of one `CalendarSyncEvent` row, captured just before it disappears."""

    connection_id: uuid.UUID
    external_calendar_id: str
    external_event_id: str | None


async def take_pending_deletions(
    reminder_id: uuid.UUID, db: AsyncSession
) -> list[PendingEventDeletion]:
    """Snapshot a reminder's sync events and drop the local rows.

    A `BackgroundTasks` callback runs after the response, so it cannot read
    these rows itself: the route reads them here (a plain, fast local read) and
    passes the result to `sync_reminder_deletion` instead of a reminder id.

    The local rows go now rather than by cascade, because deleting a reminder
    only marks it deleted. Leaving them would claim the reminder is still
    mirrored on a calendar the event is being removed from, and a restore would
    then skip re-creating it.
    """
    rows = list(
        await db.scalars(
            select(CalendarSyncEvent).where(CalendarSyncEvent.reminder_id == reminder_id)
        )
    )
    pending = [
        PendingEventDeletion(
            connection_id=row.connection_id,
            external_calendar_id=row.external_calendar_id,
            external_event_id=row.external_event_id,
        )
        for row in rows
    ]
    for row in rows:
        await db.delete(row)
    return pending


async def sync_reminder_deletion(pending: list[PendingEventDeletion]) -> None:
    """Best-effort delete of the Google Calendar events for a just-deleted reminder.

    Never raises (RF-GCAL-008): a failed remote delete only leaves a stray
    event on the member's Google calendar, which is far preferable to letting
    a Google outage block deleting a reminder in Rodiva.
    """
    settings = get_settings()
    if not settings.google_calendar_enabled or not pending:
        return

    session_maker = get_sessionmaker()
    async with session_maker() as db:
        for item in pending:
            if not item.external_event_id:
                continue
            connection = await db.get(GoogleCalendarConnection, item.connection_id)
            if connection is None:
                continue
            try:
                access_token = await refresh_access_token(connection, db)
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.delete(
                        f"{CALENDAR_API_BASE}/calendars/{item.external_calendar_id}"
                        f"/events/{item.external_event_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    # Google returns 410 Gone for an event already deleted
                    # remotely — both count as success from Rodiva's side.
                    if response.status_code not in (200, 204, 404, 410):
                        response.raise_for_status()
            except Exception as error:  # noqa: BLE001 - must never propagate
                logger.warning("Failed to delete Google Calendar event: %s", error)
                connection.last_error = str(error)
                await db.commit()
