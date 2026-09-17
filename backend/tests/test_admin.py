"""The instance status page (RF-ADM-009)."""

import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import TEST_PASSWORD, RegisterFn


async def test_status_reports_the_instance(user_client: AsyncClient) -> None:
    response = await user_client.get("/api/admin/status")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["app_name"] == "Rodiva"
    assert body["environment"] == "test"
    assert body["auth_mode"] == "local"
    assert body["database_reachable"] is True
    # The suite runs against the migrated schema, so there is a revision to name.
    assert body["migration_revision"]
    assert body["storage"]["exists"] is True


async def test_status_names_the_unconfigured_integrations(user_client: AsyncClient) -> None:
    """An operator needs to see what is off, not just what is on."""
    response = await user_client.get("/api/admin/status")

    integrations = response.json()["integrations"]
    assert set(integrations) == {"smtp", "google_calendar", "oidc", "web_push"}
    assert integrations["oidc"] is False
    assert integrations["web_push"] is False


async def test_the_notification_schedule_is_reported(user_client: AsyncClient) -> None:
    response = await user_client.get("/api/admin/status")

    tasks = response.json()["tasks"]
    assert "notifications_interval_seconds" in tasks
    # The suite drives the app through ASGITransport, which runs no lifespan, so
    # the schedule is genuinely not running — and the page says so rather than
    # repeating the configured interval as though it were fact.
    assert tasks["notifications_running"] is False


async def test_only_an_owner_can_read_the_status(register: RegisterFn) -> None:
    owner, _ = await register()
    invite = await owner.post("/api/household/invites", json={"role": "manager"})
    token = invite.json()["token"]

    manager = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        joined = await manager.post(
            "/auth/register",
            json={
                "email": f"{uuid.uuid4().hex}@example.com",
                "password": TEST_PASSWORD,
                "invite_token": token,
            },
        )
        assert joined.status_code == 201

        response = await manager.get("/api/admin/status")
        assert response.status_code == 403
    finally:
        await manager.aclose()
