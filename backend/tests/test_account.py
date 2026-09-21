import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app
from tests.conftest import TEST_PASSWORD, RegisterFn


async def test_session_revocation_is_enforced_and_scoped(register: RegisterFn) -> None:
    owner, body = await register()
    other, _ = await register()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as second:
        await second.post(
            "/auth/login", json={"email": body["user"]["email"], "password": TEST_PASSWORD}
        )
        rows = (await owner.get("/auth/sessions")).json()
        assert len(rows) == 2
        target = next(row for row in rows if not row["current"])
        assert (await other.delete(f"/auth/sessions/{target['id']}")).status_code == 404
        assert (await owner.delete(f"/auth/sessions/{target['id']}")).status_code == 204
        assert (await second.get("/auth/me")).status_code == 401
        assert (await owner.get("/auth/me")).status_code == 200
        cookie = owner.cookies.get("rodiva_session")
        assert (await owner.post("/auth/logout-all")).status_code == 204
        second.cookies.set("rodiva_session", cookie)
        assert (await second.get("/auth/me")).status_code == 401


async def test_logout_revokes_a_copied_cookie(register: RegisterFn) -> None:
    owner, _ = await register()
    cookie = owner.cookies.get("rodiva_session")
    await owner.post("/auth/logout")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as copied:
        copied.cookies.set("rodiva_session", cookie)
        assert (await copied.get("/auth/me")).status_code == 401


async def test_password_change_ends_other_sessions(register: RegisterFn) -> None:
    owner, body = await register()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as second:
        await second.post(
            "/auth/login", json={"email": body["user"]["email"], "password": TEST_PASSWORD}
        )
        response = await owner.post(
            "/auth/password",
            json={"current_password": "wrong", "new_password": "a-different-password"},
        )
        assert response.status_code == 400
        response = await owner.post(
            "/auth/password",
            json={"current_password": TEST_PASSWORD, "new_password": "a-different-password"},
        )
        assert response.status_code == 204
        assert (await owner.get("/auth/me")).status_code == 200
        assert (await second.get("/auth/me")).status_code == 401
        assert (
            await second.post(
                "/auth/login", json={"email": body["user"]["email"], "password": TEST_PASSWORD}
            )
        ).status_code == 401
        assert (
            await second.post(
                "/auth/login",
                json={"email": body["user"]["email"], "password": "a-different-password"},
            )
        ).status_code == 200


@pytest.mark.parametrize("locale", ["pt-PT", "en", "fr", "es"])
async def test_profile_is_persistent_and_validated(user_client: AsyncClient, locale: str) -> None:
    response = await user_client.patch(
        "/auth/profile", json={"name": "Maria", "locale": locale, "timezone": "Atlantic/Azores"}
    )
    assert response.status_code == 200
    profile = (await user_client.get("/auth/me")).json()["user"]
    assert (profile["name"], profile["locale"], profile["timezone"]) == (
        "Maria",
        locale,
        "Atlantic/Azores",
    )
    assert (
        await user_client.patch("/auth/profile", json={"timezone": "Invalid/Zone"})
    ).status_code == 422
    assert (await user_client.patch("/auth/profile", json={"locale": "unknown"})).status_code == 422
    assert (await user_client.patch("/auth/profile", json={"name": "Ana"})).json()[
        "locale"
    ] == locale


async def test_household_switch_changes_access(register: RegisterFn) -> None:
    owner, owner_body = await register()
    member, member_body = await register()
    vehicle = (await owner.post("/api/vehicles", json={"name": "Shared"})).json()
    invite = (await owner.post("/api/household/invites", json={"role": "reader"})).json()
    assert (await member.post(f"/auth/invites/{invite['token']}/accept")).status_code == 200
    assert (await member.get("/auth/me")).json()["membership"]["household_id"] == owner_body[
        "membership"
    ]["household_id"]
    assert (await member.get(f"/api/vehicles/{vehicle['id']}")).status_code == 200
    assert (await member.post("/api/vehicles", json={"name": "Forbidden"})).status_code == 403
    assert len((await member.get("/auth/households")).json()) == 2
    own_id = member_body["membership"]["household_id"]
    assert (await member.post(f"/auth/households/{own_id}/activate")).status_code == 200
    assert (await member.get(f"/api/vehicles/{vehicle['id']}")).status_code == 404
    assert (await member.post(f"/auth/households/{uuid.uuid4()}/activate")).status_code == 404


async def test_invite_email_and_closed_registration(register: RegisterFn) -> None:
    owner, _ = await register()
    member, _ = await register()
    email = f"{uuid.uuid4().hex}@example.com"
    invite = (
        await owner.post("/api/household/invites", json={"role": "reader", "email": email})
    ).json()
    assert (await member.post(f"/auth/invites/{invite['token']}/accept")).status_code == 403
    settings = get_settings()
    previous = settings.allow_public_registration
    settings.allow_public_registration = False
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as newcomer:
            response = await newcomer.post(
                "/auth/register",
                json={"email": email, "password": TEST_PASSWORD, "household_name": "Blocked"},
            )
            assert response.status_code == 403
            response = await newcomer.post(
                "/auth/register",
                json={
                    "email": "wrong@example.com",
                    "password": TEST_PASSWORD,
                    "invite_token": invite["token"],
                },
            )
            assert response.status_code == 403
            response = await newcomer.post(
                "/auth/register",
                json={"email": email, "password": TEST_PASSWORD, "invite_token": invite["token"]},
            )
            assert response.status_code == 201
    finally:
        settings.allow_public_registration = previous
