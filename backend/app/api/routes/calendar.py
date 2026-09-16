import contextlib
import hashlib
import secrets
import uuid
from datetime import UTC, date, datetime, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.core.security import issue_google_oauth_state, read_google_oauth_state
from app.models import (
    CalendarFeed,
    ExpenseRecord,
    GoogleCalendarConnection,
    Membership,
    Plan,
    Reminder,
    Vehicle,
)
from app.schemas.calendar import CalendarFeedCreated, CalendarFeedStatus
from app.schemas.google_calendar import (
    GoogleCalendarAuthorizeUrl,
    GoogleCalendarConnectionIn,
    GoogleCalendarOption,
    GoogleCalendarStatus,
)
from app.services import google_calendar
from app.services.token_crypto import decrypt, encrypt

router = APIRouter(tags=["calendar"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def _ics_event(kind: str, item_id: object, on: date, title: str, vehicle: str) -> list[str]:
    return [
        "BEGIN:VEVENT",
        f"UID:{kind}-{item_id}@rodiva",
        f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{on.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{(on + timedelta(days=1)).strftime('%Y%m%d')}",
        f"SUMMARY:{_ics_escape(title)}",
        f"DESCRIPTION:{_ics_escape(f'{vehicle} · {kind}')}",
        "END:VEVENT",
    ]


@router.get("/calendar-feed", response_model=CalendarFeedStatus)
async def calendar_feed_status(
    user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> CalendarFeedStatus:
    feed = await db.scalar(
        select(CalendarFeed)
        .where(
            CalendarFeed.user_id == user.id,
            CalendarFeed.household_id == membership.household_id,
            CalendarFeed.revoked_at.is_(None),
        )
        .order_by(CalendarFeed.created_at.desc())
    )
    return CalendarFeedStatus(active=feed is not None, created_at=feed.created_at if feed else None)


@router.post(
    "/calendar-feed", response_model=CalendarFeedCreated, status_code=status.HTTP_201_CREATED
)
async def create_calendar_feed(
    user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> CalendarFeedCreated:
    existing = await db.scalars(
        select(CalendarFeed).where(
            CalendarFeed.user_id == user.id,
            CalendarFeed.household_id == membership.household_id,
            CalendarFeed.revoked_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for feed in existing:
        feed.revoked_at = now
    token = secrets.token_urlsafe(32)
    feed = CalendarFeed(
        user_id=user.id,
        household_id=membership.household_id,
        token_hash=_hash_token(token),
    )
    db.add(feed)
    await db.commit()
    await db.refresh(feed)
    return CalendarFeedCreated(
        active=True,
        created_at=feed.created_at,
        token=token,
        feed_path=f"/api/calendar/{token}.ics",
    )


@router.delete("/calendar-feed", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_calendar_feed(
    user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> None:
    feeds = await db.scalars(
        select(CalendarFeed).where(
            CalendarFeed.user_id == user.id,
            CalendarFeed.household_id == membership.household_id,
            CalendarFeed.revoked_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for feed in feeds:
        feed.revoked_at = now
    await db.commit()


@router.get("/calendar/{token}.ics", response_class=Response)
async def read_calendar_feed(token: str, db: DbSession) -> Response:
    if len(token) < 32 or len(token) > 128:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")
    feed = await db.scalar(
        select(CalendarFeed).where(
            CalendarFeed.token_hash == _hash_token(token), CalendarFeed.revoked_at.is_(None)
        )
    )
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar not found")

    vehicle_result = await db.scalars(
        select(Vehicle).where(
            Vehicle.household_id == feed.household_id, Vehicle.deleted_at.is_(None)
        )
    )
    vehicle_map = {vehicle.id: vehicle.name for vehicle in vehicle_result}
    vehicle_ids = list(vehicle_map)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Rodiva//Calendar//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Rodiva",
    ]
    if vehicle_ids:
        reminder_result = await db.scalars(
            select(Reminder).where(
                Reminder.vehicle_id.in_(vehicle_ids),
                Reminder.status != "completed",
                Reminder.due_date.is_not(None),
            )
        )
        for reminder in reminder_result:
            if reminder.due_date:
                lines.extend(
                    _ics_event(
                        "reminder",
                        reminder.id,
                        reminder.due_date,
                        reminder.title,
                        vehicle_map[reminder.vehicle_id],
                    )
                )

        expense_result = await db.scalars(
            select(ExpenseRecord).where(
                ExpenseRecord.vehicle_id.in_(vehicle_ids),
                ExpenseRecord.status.in_(["planned", "pending"]),
            )
        )
        for expense in expense_result:
            lines.extend(
                _ics_event(
                    "expense",
                    expense.id,
                    expense.issued_on,
                    expense.category,
                    vehicle_map[expense.vehicle_id],
                )
            )

        plan_result = await db.scalars(
            select(Plan).where(
                Plan.vehicle_id.in_(vehicle_ids),
                Plan.stage != "completed",
                Plan.due_date.is_not(None),
            )
        )
        for plan in plan_result:
            if plan.due_date:
                lines.extend(
                    _ics_event(
                        "plan",
                        plan.id,
                        plan.due_date,
                        plan.description,
                        vehicle_map[plan.vehicle_id],
                    )
                )
    lines.append("END:VCALENDAR")
    return Response(
        content="\r\n".join(lines) + "\r\n",
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'inline; filename="rodiva.ics"',
            "Cache-Control": "no-store",
        },
    )


# --- Google Calendar (RF-GCAL-001..009) --------------------------------------
# A second, separate integration alongside the ICS feed above: per-member,
# OAuth-based, and it writes events into a Google calendar the member picked.


async def _own_google_connection(
    user: CurrentUser, db: DbSession
) -> GoogleCalendarConnection | None:
    connection: GoogleCalendarConnection | None = await db.scalar(
        select(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == user.id)
    )
    return connection


@router.get("/calendar/google/status", response_model=GoogleCalendarStatus)
async def google_calendar_status(
    user: CurrentUser, settings: AppSettings, db: DbSession
) -> GoogleCalendarStatus:
    if not settings.google_calendar_enabled:
        return GoogleCalendarStatus(configured=False, connected=False)
    connection = await _own_google_connection(user, db)
    if connection is None:
        return GoogleCalendarStatus(configured=True, connected=False)
    return GoogleCalendarStatus(
        configured=True,
        connected=True,
        google_account_email=connection.google_account_email,
        calendar_id=connection.calendar_id,
        synced_vehicle_ids=[uuid.UUID(item) for item in connection.synced_vehicle_ids],
        status=connection.status,
        last_error=connection.last_error,
    )


@router.get("/calendar/google/connect", response_model=GoogleCalendarAuthorizeUrl)
async def google_calendar_connect(
    user: CurrentUser, settings: AppSettings
) -> GoogleCalendarAuthorizeUrl:
    if not settings.google_calendar_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Calendar integration is not configured on this server",
        )
    state = issue_google_oauth_state(user.id)
    return GoogleCalendarAuthorizeUrl(authorize_url=google_calendar.build_authorize_url(state))


@router.get("/calendar/google/callback", response_class=Response)
async def google_calendar_callback(
    code: str, state: str, settings: AppSettings, db: DbSession
) -> Response:
    frontend_error_redirect = f"{settings.public_frontend_url}/settings?google_calendar=error"
    if not settings.google_calendar_enabled:
        return Response(
            status_code=status.HTTP_302_FOUND, headers={"Location": frontend_error_redirect}
        )
    user_id = read_google_oauth_state(state)
    if user_id is None:
        return Response(
            status_code=status.HTTP_302_FOUND, headers={"Location": frontend_error_redirect}
        )

    membership = await db.scalar(
        select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at)
    )
    if membership is None:
        return Response(
            status_code=status.HTTP_302_FOUND, headers={"Location": frontend_error_redirect}
        )

    try:
        tokens = await google_calendar.exchange_code(code)
        account_email = await google_calendar.fetch_account_email(tokens["access_token"])
    except httpx.HTTPError:
        return Response(
            status_code=status.HTTP_302_FOUND, headers={"Location": frontend_error_redirect}
        )

    connection = await db.scalar(
        select(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == user_id)
    )
    expires_at = datetime.now(UTC) + timedelta(seconds=tokens.get("expires_in", 3600))
    if connection is None:
        connection = GoogleCalendarConnection(
            user_id=user_id,
            household_id=membership.household_id,
            google_account_email=account_email,
            access_token_encrypted=encrypt(tokens["access_token"]),
            refresh_token_encrypted=encrypt(tokens.get("refresh_token", "")),
            token_expires_at=expires_at,
            status="pending_setup",
        )
        db.add(connection)
    else:
        connection.google_account_email = account_email
        connection.access_token_encrypted = encrypt(tokens["access_token"])
        # Google only returns a refresh_token on first consent; keep the
        # existing one if this is a reconnect that didn't get a fresh one.
        if tokens.get("refresh_token"):
            connection.refresh_token_encrypted = encrypt(tokens["refresh_token"])
        connection.token_expires_at = expires_at
        connection.status = "pending_setup"
        connection.calendar_id = None
        connection.last_error = None
    await db.commit()

    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": f"{settings.public_frontend_url}/settings?google_calendar=connected"},
    )


@router.get("/calendar/google/calendars", response_model=list[GoogleCalendarOption])
async def google_calendar_list_calendars(
    user: CurrentUser, settings: AppSettings, db: DbSession
) -> list[GoogleCalendarOption]:
    if not settings.google_calendar_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Calendar integration is not configured on this server",
        )
    connection = await _own_google_connection(user, db)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Google connection")
    access_token = await google_calendar.refresh_access_token(connection, db)
    calendars = await google_calendar.list_calendars(access_token)
    return [GoogleCalendarOption(**item) for item in calendars]


@router.post("/calendar/google/connection", response_model=GoogleCalendarStatus)
async def google_calendar_finalize_connection(
    payload: GoogleCalendarConnectionIn,
    user: CurrentUser,
    membership: CurrentMembership,
    settings: AppSettings,
    db: DbSession,
) -> GoogleCalendarStatus:
    if not settings.google_calendar_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Calendar integration is not configured on this server",
        )
    connection = await _own_google_connection(user, db)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No Google connection")

    for vehicle_id in payload.vehicle_ids:
        await _vehicle_in_household(vehicle_id, membership, db)

    connection.calendar_id = payload.calendar_id
    connection.synced_vehicle_ids = [str(vehicle_id) for vehicle_id in payload.vehicle_ids]
    connection.status = "active"
    connection.last_error = None
    await db.commit()

    return GoogleCalendarStatus(
        configured=True,
        connected=True,
        google_account_email=connection.google_account_email,
        calendar_id=connection.calendar_id,
        synced_vehicle_ids=payload.vehicle_ids,
        status=connection.status,
        last_error=connection.last_error,
    )


@router.delete("/calendar/google/connection", status_code=status.HTTP_204_NO_CONTENT)
async def google_calendar_disconnect(user: CurrentUser, db: DbSession) -> None:
    connection = await _own_google_connection(user, db)
    if connection is None:
        return
    with contextlib.suppress(Exception):
        # Best-effort remote revoke (RF-GCAL-007) — local cleanup proceeds either way.
        await google_calendar.revoke_token(decrypt(connection.refresh_token_encrypted))
    await db.delete(connection)
    await db.commit()
