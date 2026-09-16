from datetime import date, timedelta
from unittest.mock import patch

from httpx import AsyncClient

from tests.conftest import RegisterFn


async def _vehicle(client: AsyncClient, name: str = "Golf") -> str:
    response = await client.post("/api/v1/vehicles", json={"name": name, "distance_unit": "km"})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _reminder(client: AsyncClient, vehicle_id: str, title: str, days_ahead: int) -> str:
    due = (date.today() + timedelta(days=days_ahead)).isoformat()
    response = await client.post(
        f"/api/v1/vehicles/{vehicle_id}/reminders", json={"title": title, "due_date": due}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def test_an_urgent_reminder_reaches_the_inbox_once(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    await _reminder(client, vehicle_id, "Inspeção", 3)

    first = (await client.post("/api/v1/notifications/run")).json()
    assert first["created"] == 1

    # Running again changes nothing: the same reminder at the same urgency is
    # already in the inbox (RF-NOT-004).
    second = (await client.post("/api/v1/notifications/run")).json()
    assert second["created"] == 0

    inbox = (await client.get("/api/v1/notifications")).json()
    assert inbox["unread"] == 1
    assert inbox["items"][0]["title"] == "Inspeção"
    assert inbox["items"][0]["context"]["vehicle_name"] == "Golf"


async def test_a_reminder_that_becomes_more_pressing_notifies_again(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    reminder_id = await _reminder(client, vehicle_id, "Selo", 20)

    assert (await client.post("/api/v1/notifications/run")).json()["created"] == 1

    # Pull the due date closer: urgent becomes very_urgent, which is new news.
    await client.patch(
        f"/api/v1/vehicles/{vehicle_id}/reminders/{reminder_id}",
        json={"due_date": (date.today() + timedelta(days=2)).isoformat()},
    )
    assert (await client.post("/api/v1/notifications/run")).json()["created"] == 1
    assert (await client.get("/api/v1/notifications")).json()["unread"] == 2


async def test_a_distant_reminder_stays_quiet_until_the_threshold_says_otherwise(
    register: RegisterFn,
) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    await _reminder(client, vehicle_id, "Revisão", 60)

    assert (await client.post("/api/v1/notifications/run")).json()["created"] == 0

    await client.put(
        "/api/v1/notifications/preferences",
        json={"channel_inapp": True, "channel_email": False, "min_urgency": "upcoming"},
    )
    assert (await client.post("/api/v1/notifications/run")).json()["created"] == 1


async def test_preferences_can_limit_which_vehicles_are_heard_about(register: RegisterFn) -> None:
    client, _ = await register()
    watched = await _vehicle(client, "Golf")
    ignored = await _vehicle(client, "Berlingo")
    await _reminder(client, watched, "Inspeção", 3)
    await _reminder(client, ignored, "Selo", 3)

    await client.put(
        "/api/v1/notifications/preferences",
        json={
            "channel_inapp": True,
            "channel_email": False,
            "min_urgency": "urgent",
            "vehicle_ids": [watched],
        },
    )
    assert (await client.post("/api/v1/notifications/run")).json()["created"] == 1
    items = (await client.get("/api/v1/notifications")).json()["items"]
    assert [item["title"] for item in items] == ["Inspeção"]


async def test_marking_read(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    await _reminder(client, vehicle_id, "Inspeção", 3)
    await _reminder(client, vehicle_id, "Selo", 1)
    await client.post("/api/v1/notifications/run")

    inbox = (await client.get("/api/v1/notifications")).json()
    assert inbox["unread"] == 2

    first = inbox["items"][0]["id"]
    assert (await client.post(f"/api/v1/notifications/{first}/read")).status_code == 204
    assert (await client.get("/api/v1/notifications")).json()["unread"] == 1

    assert (await client.post("/api/v1/notifications/read-all")).status_code == 204
    assert (await client.get("/api/v1/notifications")).json()["unread"] == 0
    assert (await client.get("/api/v1/notifications?unread_only=true")).json()["items"] == []


async def test_an_inbox_belongs_to_its_member(register: RegisterFn) -> None:
    owner, _ = await register()
    member, _ = await register()
    invite = (await owner.post("/api/household/invites", json={"role": "reader"})).json()
    await member.post(f"/auth/invites/{invite['token']}/accept")

    vehicle_id = await _vehicle(owner)
    await _reminder(owner, vehicle_id, "Inspeção", 3)
    await owner.post("/api/v1/notifications/run")

    # Both members are told, but each only sees their own copy.
    owner_inbox = (await owner.get("/api/v1/notifications")).json()
    member_inbox = (await member.get("/api/v1/notifications")).json()
    assert owner_inbox["unread"] == 1
    assert member_inbox["unread"] == 1
    assert owner_inbox["items"][0]["id"] != member_inbox["items"][0]["id"]

    other = member_inbox["items"][0]["id"]
    assert (await owner.post(f"/api/v1/notifications/{other}/read")).status_code == 404


async def test_email_is_attempted_when_smtp_is_configured(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    await _reminder(client, vehicle_id, "Inspeção", 3)
    await client.put(
        "/api/v1/notifications/preferences",
        json={"channel_inapp": True, "channel_email": True, "min_urgency": "urgent"},
    )

    with (
        patch("app.services.notifications.get_settings") as get_settings,
        patch("app.services.notifications._send") as send,
    ):
        configured = get_settings.return_value
        configured.smtp_host = "smtp.example.com"
        configured.smtp_from = "rodiva@example.com"
        configured.smtp_port = 587
        configured.smtp_starttls = True
        configured.smtp_username = ""
        configured.smtp_password = ""
        configured.public_frontend_url = "http://localhost:5173"
        result = (await client.post("/api/v1/notifications/run")).json()
    assert result["created"] == 1
    assert result["delivered"] == 1
    assert send.called


async def test_a_failing_send_is_recorded_not_raised(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    await _reminder(client, vehicle_id, "Inspeção", 3)
    await client.put(
        "/api/v1/notifications/preferences",
        json={"channel_inapp": True, "channel_email": True, "min_urgency": "urgent"},
    )

    with (
        patch("app.services.notifications.get_settings") as get_settings,
        patch("app.services.notifications._send", side_effect=OSError("no route to host")),
    ):
        configured = get_settings.return_value
        configured.smtp_host = "smtp.example.com"
        configured.smtp_from = "rodiva@example.com"
        response = await client.post("/api/v1/notifications/run")

    # The run still succeeds (RF-NOT-008) and the failure is counted.
    assert response.status_code == 200
    assert response.json()["failed"] == 1
    # The in-app copy is unaffected by the email channel failing.
    assert (await client.get("/api/v1/notifications")).json()["unread"] == 1


async def test_only_an_owner_can_trigger_a_run(register: RegisterFn) -> None:
    owner, _ = await register()
    member, _ = await register()
    invite = (await owner.post("/api/household/invites", json={"role": "editor"})).json()
    await member.post(f"/auth/invites/{invite['token']}/accept")
    assert (await member.post("/api/v1/notifications/run")).status_code == 403


async def test_quiet_hours_hold_email_without_losing_it(register: RegisterFn) -> None:
    from datetime import UTC, datetime

    from app.services.notifications import _in_quiet_hours

    class Preference:
        quiet_hours_start = 22
        quiet_hours_end = 7

    midnight = datetime(2026, 1, 1, 0, 30, tzinfo=UTC)
    midday = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    # A window that wraps past midnight covers both ends of the day.
    assert _in_quiet_hours(Preference(), "UTC", midnight) is True
    assert _in_quiet_hours(Preference(), "UTC", midday) is False

    class Daytime:
        quiet_hours_start = 9
        quiet_hours_end = 17

    assert _in_quiet_hours(Daytime(), "UTC", midday) is True
    assert _in_quiet_hours(Daytime(), "UTC", midnight) is False
