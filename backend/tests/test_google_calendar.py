import uuid
from datetime import date

import httpx
import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models import CalendarSyncEvent

TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
EVENTS_URL_RE = r"https://www\.googleapis\.com/calendar/v3/calendars/[^/]+/events$"
EVENT_URL_RE = r"https://www\.googleapis\.com/calendar/v3/calendars/[^/]+/events/[^/]+$"


@pytest.fixture
def configured_google(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(settings, "google_client_secret", "test-client-secret")
    return settings


def _token_exchange(request: httpx.Request) -> httpx.Response:
    body = request.content.decode()
    if "grant_type=refresh_token" in body:
        return httpx.Response(
            200, json={"access_token": "refreshed-access-token", "expires_in": 3600}
        )
    return httpx.Response(
        200,
        json={
            "access_token": "initial-access-token",
            "refresh_token": "initial-refresh-token",
            "expires_in": 3600,
            "id_token": "fake-id-token",
        },
    )


def _mock_oauth() -> None:
    respx.post(TOKEN_URL).mock(side_effect=_token_exchange)
    respx.get(USERINFO_URL).mock(
        return_value=httpx.Response(200, json={"email": "member@example.com"})
    )
    respx.get(CALENDAR_LIST_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {"id": "primary", "summary": "Primary"},
                    {"id": "cal2", "summary": "Family"},
                ]
            },
        )
    )
    respx.post(REVOKE_URL).mock(return_value=httpx.Response(200))


async def _vehicle(client: AsyncClient, name: str = "Carro de teste") -> str:
    response = await client.post("/api/vehicles", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def _connect_and_activate(client: AsyncClient, vehicle_ids: list[str]) -> None:
    """Run the OAuth handshake + calendar selection, leaving an active connection."""
    connect = await client.get("/api/calendar/google/connect")
    assert connect.status_code == 200
    state = httpx.URL(connect.json()["authorize_url"]).params["state"]

    callback = await client.get(
        "/api/calendar/google/callback", params={"code": "auth-code", "state": state}
    )
    assert callback.status_code == 302
    assert "google_calendar=connected" in callback.headers["location"]

    calendars = await client.get("/api/calendar/google/calendars")
    assert calendars.status_code == 200
    assert {item["id"] for item in calendars.json()} == {"primary", "cal2"}

    finalize = await client.post(
        "/api/calendar/google/connection",
        json={"calendar_id": "primary", "vehicle_ids": vehicle_ids},
    )
    assert finalize.status_code == 200
    assert finalize.json()["status"] == "active"


async def _sync_event_for(reminder_id: str) -> CalendarSyncEvent | None:
    async with get_sessionmaker()() as db:
        return await db.scalar(
            select(CalendarSyncEvent).where(CalendarSyncEvent.reminder_id == uuid.UUID(reminder_id))
        )


async def test_status_reports_not_configured_by_default(user_client: AsyncClient) -> None:
    response = await user_client.get("/api/calendar/google/status")
    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "connected": False,
        "google_account_email": None,
        "calendar_id": None,
        "synced_vehicle_ids": [],
        "status": None,
        "last_error": None,
    }


async def test_connect_is_unavailable_without_credentials(user_client: AsyncClient) -> None:
    response = await user_client.get("/api/calendar/google/connect")
    assert response.status_code == 503


@respx.mock
async def test_connect_returns_authorize_url_when_configured(
    user_client: AsyncClient, configured_google
) -> None:
    response = await user_client.get("/api/calendar/google/connect")
    assert response.status_code == 200
    authorize_url = httpx.URL(response.json()["authorize_url"])
    assert authorize_url.params["client_id"] == "test-client-id"
    assert "calendar.events" in authorize_url.params["scope"]


@respx.mock
async def test_full_google_calendar_connect_and_sync_flow(
    user_client: AsyncClient, configured_google
) -> None:
    _mock_oauth()
    events_post = respx.post(url__regex=EVENTS_URL_RE).mock(
        return_value=httpx.Response(200, json={"id": "evt-1"})
    )
    events_patch = respx.patch(url__regex=EVENT_URL_RE).mock(
        return_value=httpx.Response(200, json={"id": "evt-1"})
    )
    events_delete = respx.delete(url__regex=EVENT_URL_RE).mock(return_value=httpx.Response(204))

    vehicle_id = await _vehicle(user_client)

    # Before connecting, status is configured but not connected.
    status_before = await user_client.get("/api/calendar/google/status")
    assert status_before.json() == {
        "configured": True,
        "connected": False,
        "google_account_email": None,
        "calendar_id": None,
        "synced_vehicle_ids": [],
        "status": None,
        "last_error": None,
    }

    await _connect_and_activate(user_client, [vehicle_id])

    status_after = await user_client.get("/api/calendar/google/status")
    body = status_after.json()
    assert body["connected"] is True
    assert body["google_account_email"] == "member@example.com"
    assert body["calendar_id"] == "primary"
    assert body["synced_vehicle_ids"] == [vehicle_id]
    assert body["status"] == "active"

    # Creating a due-dated reminder syncs it (background task runs before the
    # test's await returns, per Starlette's synchronous background execution).
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders",
        json={"title": "Trocar óleo", "due_date": date.today().isoformat()},
    )
    assert created.status_code == 201
    reminder_id = created.json()["id"]
    assert events_post.called
    sync_event = await _sync_event_for(reminder_id)
    assert sync_event is not None
    assert sync_event.status == "synced"
    assert sync_event.external_event_id == "evt-1"

    # Updating it PATCHes the existing event rather than creating a new one.
    updated = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}",
        json={"title": "Trocar óleo e filtro"},
    )
    assert updated.status_code == 200
    assert events_patch.called
    assert events_post.call_count == 1

    # Completing it updates (not deletes) the event.
    completed = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/complete"
    )
    assert completed.status_code == 200
    sync_event = await _sync_event_for(reminder_id)
    assert sync_event is not None
    assert sync_event.status == "synced"

    # A distance-only reminder (no due_date) is never synced.
    distance_only = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders", json={"title": "Pneus", "due_odometer": 50_000}
    )
    assert distance_only.status_code == 201
    assert await _sync_event_for(distance_only.json()["id"]) is None
    assert events_post.call_count == 1

    # Deleting the reminder deletes the remote event and the bookkeeping row.
    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}")
    assert deleted.status_code == 204
    assert events_delete.called
    assert await _sync_event_for(reminder_id) is None

    # Disconnecting best-effort revokes the token and removes the connection.
    disconnect = await user_client.delete("/api/calendar/google/connection")
    assert disconnect.status_code == 204
    status_final = await user_client.get("/api/calendar/google/status")
    assert status_final.json()["connected"] is False


@respx.mock
async def test_sync_failure_is_recorded_without_failing_the_request(
    user_client: AsyncClient, configured_google
) -> None:
    _mock_oauth()
    respx.post(url__regex=EVENTS_URL_RE).mock(return_value=httpx.Response(500, text="boom"))

    vehicle_id = await _vehicle(user_client)
    await _connect_and_activate(user_client, [vehicle_id])

    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders",
        json={"title": "Inspeção", "due_date": date.today().isoformat()},
    )
    assert created.status_code == 201

    sync_event = await _sync_event_for(created.json()["id"])
    assert sync_event is not None
    assert sync_event.status == "error"
    assert sync_event.last_error

    status_response = await user_client.get("/api/calendar/google/status")
    assert status_response.json()["last_error"]


@respx.mock
async def test_google_calendar_connection_is_private_to_each_member(
    register, configured_google
) -> None:
    _mock_oauth()
    respx.post(url__regex=EVENTS_URL_RE).mock(
        return_value=httpx.Response(200, json={"id": "evt-1"})
    )

    owner, _ = await register(household_name="Household A")
    vehicle_id = await _vehicle(owner)
    await _connect_and_activate(owner, [vehicle_id])

    other, _ = await register(household_name="Household B")
    other_status = await other.get("/api/calendar/google/status")
    assert other_status.json() == {
        "configured": True,
        "connected": False,
        "google_account_email": None,
        "calendar_id": None,
        "synced_vehicle_ids": [],
        "status": None,
        "last_error": None,
    }
    assert (await other.get("/api/calendar/google/calendars")).status_code == 404


async def test_connection_finalize_rejects_a_vehicle_outside_the_household(
    user_client: AsyncClient, configured_google
) -> None:
    with respx.mock:
        _mock_oauth()
        connect = await user_client.get("/api/calendar/google/connect")
        state = httpx.URL(connect.json()["authorize_url"]).params["state"]
        await user_client.get(
            "/api/calendar/google/callback", params={"code": "auth-code", "state": state}
        )

    response = await user_client.post(
        "/api/calendar/google/connection",
        json={"calendar_id": "primary", "vehicle_ids": [str(uuid.uuid4())]},
    )
    assert response.status_code == 404
