from httpx import AsyncClient

from tests.conftest import RegisterFn


async def _join(owner: AsyncClient, member: AsyncClient, role: str = "reader") -> str:
    """Put `member` in the owner's household and hand back their user id."""
    invite = (await owner.post("/api/household/invites", json={"role": role})).json()
    accepted = await member.post(f"/auth/invites/{invite['token']}/accept")
    assert accepted.status_code == 200, accepted.text
    return (await member.get("/auth/me")).json()["user"]["id"]


async def test_member_and_invite_changes_are_recorded(register: RegisterFn) -> None:
    owner, _ = await register()
    member, _ = await register()
    member_id = await _join(owner, member)

    await owner.patch(f"/api/household/members/{member_id}", json={"role": "editor"})
    await owner.delete(f"/api/household/members/{member_id}")

    events = (await owner.get("/api/v1/audit")).json()["items"]
    actions = [event["action"] for event in events]
    assert actions == ["member.removed", "member.role_changed", "invite.created"]

    role_change = events[1]
    assert role_change["context"] == {"from": "reader", "to": "editor"}
    assert role_change["entity_id"] == member_id
    # The actor is named in the row, so the trail still reads once an account goes.
    assert role_change["actor_label"]


async def test_api_key_lifecycle_is_recorded(register: RegisterFn) -> None:
    owner, _ = await register()
    key = (await owner.post("/api/v1/api-keys", json={"name": "n8n", "scope": "read"})).json()
    await owner.delete(f"/api/v1/api-keys/{key['id']}")

    events = (await owner.get("/api/v1/audit?action=api_key")).json()["items"]
    assert [event["action"] for event in events] == ["api_key.revoked", "api_key.created"]
    assert events[1]["context"]["scope"] == "read"


async def test_trail_is_scoped_to_the_household(register: RegisterFn) -> None:
    owner, _ = await register()
    other, _ = await register()
    await owner.post("/api/household/invites", json={"role": "reader"})

    assert len((await owner.get("/api/v1/audit")).json()["items"]) == 1
    # A separate household sees none of it, even though the rows exist.
    assert (await other.get("/api/v1/audit")).json()["items"] == []


async def test_readers_and_editors_cannot_read_the_trail(register: RegisterFn) -> None:
    owner, _ = await register()
    member, _ = await register()
    await _join(owner, member, role="editor")
    assert (await member.get("/api/v1/audit")).status_code == 403


async def test_filtering_and_paging(register: RegisterFn) -> None:
    owner, _ = await register()
    for _ in range(3):
        await owner.post("/api/household/invites", json={"role": "reader"})

    first = (await owner.get("/api/v1/audit?limit=2")).json()
    assert len(first["items"]) == 2
    assert first["next_before"] is not None

    second = (await owner.get(f"/api/v1/audit?limit=2&before={first['next_before']}")).json()
    assert len(second["items"]) == 1
    assert second["next_before"] is None
    assert {item["id"] for item in first["items"]}.isdisjoint(
        {item["id"] for item in second["items"]}
    )

    assert (await owner.get("/api/v1/audit?action=api_key")).json()["items"] == []
