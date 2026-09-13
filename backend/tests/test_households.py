import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import TEST_PASSWORD, RegisterFn


async def test_create_invite_and_register_joins_the_household(register: RegisterFn) -> None:
    owner, owner_body = await register(household_name="Alves household")

    invite = await owner.post("/api/household/invites", json={"role": "editor"})
    assert invite.status_code == 201
    token = invite.json()["token"]

    invitee = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        response = await invitee.post(
            "/auth/register",
            json={
                "email": f"{uuid.uuid4().hex}@example.com",
                "password": TEST_PASSWORD,
                "invite_token": token,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["membership"]["household_id"] == owner_body["membership"]["household_id"]
        assert body["membership"]["role"] == "editor"
    finally:
        await invitee.aclose()

    members = await owner.get("/api/household/members")
    assert members.status_code == 200
    assert sorted(member["role"] for member in members.json()) == ["editor", "owner"]


async def test_expired_or_used_invite_is_rejected(register: RegisterFn) -> None:
    owner, _ = await register()
    invite = await owner.post("/api/household/invites", json={"role": "reader"})
    token = invite.json()["token"]

    revoke = await owner.delete(f"/api/household/invites/{invite.json()['id']}")
    assert revoke.status_code == 204

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        preview = await client.get(f"/auth/invites/{token}")
        assert preview.status_code == 404
    finally:
        await client.aclose()


async def test_registering_without_household_name_or_invite_is_rejected(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": f"{uuid.uuid4().hex}@example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 422


async def test_signed_in_user_can_accept_an_invite(register: RegisterFn) -> None:
    owner, _ = await register(household_name="First household")
    invite = await owner.post("/api/household/invites", json={"role": "manager"})
    token = invite.json()["token"]

    second, _ = await register(household_name="Second household")
    accepted = await second.post(f"/auth/invites/{token}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["membership"]["role"] == "manager"


async def test_only_a_manager_or_owner_can_invite(register: RegisterFn) -> None:
    owner, owner_body = await register()
    invite = await owner.post("/api/household/invites", json={"role": "reader"})
    token = invite.json()["token"]

    reader = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        joined = await reader.post(
            "/auth/register",
            json={
                "email": f"{uuid.uuid4().hex}@example.com",
                "password": TEST_PASSWORD,
                "invite_token": token,
            },
        )
        assert joined.status_code == 201

        forbidden = await reader.post("/api/household/invites", json={"role": "editor"})
        assert forbidden.status_code == 403
    finally:
        await reader.aclose()


async def test_cannot_remove_the_last_owner(user_client: AsyncClient) -> None:
    me = await user_client.get("/auth/me")
    user_id = me.json()["user"]["id"]

    response = await user_client.delete(f"/api/household/members/{user_id}")
    assert response.status_code == 409


async def test_owner_can_change_a_members_role(register: RegisterFn) -> None:
    owner, _ = await register()
    invite = await owner.post("/api/household/invites", json={"role": "editor"})
    token = invite.json()["token"]

    member = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        joined = await member.post(
            "/auth/register",
            json={
                "email": f"{uuid.uuid4().hex}@example.com",
                "password": TEST_PASSWORD,
                "invite_token": token,
            },
        )
        member_id = joined.json()["user"]["id"]

        promoted = await owner.patch(
            f"/api/household/members/{member_id}", json={"role": "manager"}
        )
        assert promoted.status_code == 200
        assert promoted.json()["role"] == "manager"
    finally:
        await member.aclose()
