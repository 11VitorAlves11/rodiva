"""Household tags, what they sit on, and filtering by them (RF-DOC-009, RF-PES-001)."""

import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import TEST_PASSWORD, RegisterFn


async def _vehicle(client: AsyncClient, name: str = "Carro de teste") -> str:
    response = await client.post("/api/vehicles", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def _tag(client: AsyncClient, name: str, color: str = "#B94A22") -> str:
    response = await client.post("/api/tags", json={"name": name, "color": color})
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_create_and_list_tags(user_client: AsyncClient) -> None:
    await _tag(user_client, "Inverno")
    await _tag(user_client, "Garantia", "#2F6F4E")

    listed = await user_client.get("/api/tags")

    assert listed.status_code == 200
    body = listed.json()
    assert [tag["name"] for tag in body] == ["Garantia", "Inverno"]
    assert all(tag["record_count"] == 0 for tag in body)


async def test_a_name_differing_only_by_accent_or_case_is_a_duplicate(
    user_client: AsyncClient,
) -> None:
    """Two tags reading the same in the picker would make the feature useless."""
    await _tag(user_client, "Inverno")

    clash = await user_client.post("/api/tags", json={"name": "INVÉRNO"})

    assert clash.status_code == 409
    assert "Inverno" in clash.json()["detail"]


async def test_a_colour_must_be_a_hex_value(user_client: AsyncClient) -> None:
    response = await user_client.post("/api/tags", json={"name": "Azul", "color": "azul"})

    assert response.status_code == 422


async def test_tagging_a_record_and_reading_it_back(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    winter = await _tag(user_client, "Inverno")
    warranty = await _tag(user_client, "Garantia")

    put = await user_client.put(
        f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [winter, warranty]}
    )

    assert put.status_code == 200
    assert [tag["name"] for tag in put.json()] == ["Garantia", "Inverno"]

    read = await user_client.get(f"/api/tags/records/vehicle/{vehicle_id}")
    assert [tag["name"] for tag in read.json()] == ["Garantia", "Inverno"]

    counted = await user_client.get("/api/tags")
    assert {tag["name"]: tag["record_count"] for tag in counted.json()} == {
        "Garantia": 1,
        "Inverno": 1,
    }


async def test_setting_tags_replaces_rather_than_adds(user_client: AsyncClient) -> None:
    """A form submission carries the full set the member wants, not a delta."""
    vehicle_id = await _vehicle(user_client)
    winter = await _tag(user_client, "Inverno")
    warranty = await _tag(user_client, "Garantia")
    await user_client.put(
        f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [winter, warranty]}
    )

    replaced = await user_client.put(
        f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [winter]}
    )

    assert [tag["name"] for tag in replaced.json()] == ["Inverno"]


async def test_tags_can_be_cleared(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    winter = await _tag(user_client, "Inverno")
    await user_client.put(f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [winter]})

    cleared = await user_client.put(f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": []})

    assert cleared.json() == []


async def test_a_tag_from_another_household_is_ignored(register: RegisterFn) -> None:
    """Sending a stranger's tag id must not attach it (RNF-SEG-001)."""
    mine, _ = await register()
    theirs, _ = await register()
    vehicle_id = await _vehicle(mine)
    foreign = await _tag(theirs, "Alheia")

    response = await mine.put(
        f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [foreign]}
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_another_households_record_cannot_be_tagged(register: RegisterFn) -> None:
    mine, _ = await register()
    theirs, _ = await register()
    their_vehicle = await _vehicle(theirs)
    my_tag = await _tag(mine, "Minha")

    response = await mine.put(
        f"/api/tags/records/vehicle/{their_vehicle}", json={"tag_ids": [my_tag]}
    )

    assert response.status_code == 404


async def test_an_unknown_kind_is_refused(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)

    response = await user_client.put(
        f"/api/tags/records/wormhole/{vehicle_id}", json={"tag_ids": []}
    )

    assert response.status_code == 404


async def test_deleting_a_tag_removes_it_from_its_records(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    winter = await _tag(user_client, "Inverno")
    await user_client.put(f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [winter]})

    deleted = await user_client.delete(f"/api/tags/{winter}")

    assert deleted.status_code == 204
    remaining = await user_client.get(f"/api/tags/records/vehicle/{vehicle_id}")
    assert remaining.json() == []


async def test_renaming_a_tag_keeps_it_on_its_records(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    winter = await _tag(user_client, "Inverno")
    await user_client.put(f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [winter]})

    renamed = await user_client.patch(f"/api/tags/{winter}", json={"name": "Pneus de inverno"})

    assert renamed.status_code == 200
    still_there = await user_client.get(f"/api/tags/records/vehicle/{vehicle_id}")
    assert [tag["name"] for tag in still_there.json()] == ["Pneus de inverno"]


async def test_search_filters_by_tag(user_client: AsyncClient) -> None:
    tagged_vehicle = await _vehicle(user_client, "Volvo V60")
    await _vehicle(user_client, "Corolla")
    winter = await _tag(user_client, "Inverno")
    await user_client.put(f"/api/tags/records/vehicle/{tagged_vehicle}", json={"tag_ids": [winter]})

    response = await user_client.get("/api/search", params={"tag_id": winter})

    assert response.status_code == 200
    body = response.json()
    assert [result["title"] for result in body] == ["Volvo V60"]
    assert [tag["name"] for tag in body[0]["tags"]] == ["Inverno"]


async def test_search_results_carry_their_tags(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client, "Volvo V60")
    winter = await _tag(user_client, "Inverno")
    await user_client.put(f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [winter]})

    response = await user_client.get("/api/search", params={"q": "Volvo"})

    result = next(item for item in response.json() if item["id"] == vehicle_id)
    assert result["tags"] == [{"id": winter, "name": "Inverno", "color": "#B94A22"}]


async def test_search_refuses_a_tag_from_another_household(register: RegisterFn) -> None:
    mine, _ = await register()
    theirs, _ = await register()
    foreign = await _tag(theirs, "Alheia")

    response = await mine.get("/api/search", params={"tag_id": foreign})

    assert response.status_code == 404


async def test_an_editor_can_tag_but_not_manage_tags(register: RegisterFn) -> None:
    """Putting a tag on a record is editing; reshaping the shared set is not (spec §2.3)."""
    owner, _ = await register()
    vehicle_id = await _vehicle(owner)
    winter = await _tag(owner, "Inverno")
    invite = await owner.post("/api/household/invites", json={"role": "editor"})
    token = invite.json()["token"]

    editor = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        joined = await editor.post(
            "/auth/register",
            json={
                "email": f"{uuid.uuid4().hex}@example.com",
                "password": TEST_PASSWORD,
                "invite_token": token,
            },
        )
        assert joined.status_code == 201

        tagged = await editor.put(
            f"/api/tags/records/vehicle/{vehicle_id}", json={"tag_ids": [winter]}
        )
        assert tagged.status_code == 200

        forbidden = await editor.post("/api/tags", json={"name": "Nao devia"})
        assert forbidden.status_code == 403
    finally:
        await editor.aclose()


async def test_purging_a_record_clears_its_tags(user_client: AsyncClient) -> None:
    """Nothing cascades: the link carries no foreign key to the record it names."""
    vehicle_id = await _vehicle(user_client)
    note = await user_client.post(
        f"/api/vehicles/{vehicle_id}/notes", json={"title": "Nota", "content": "Texto"}
    )
    assert note.status_code == 201
    note_id = note.json()["id"]
    winter = await _tag(user_client, "Inverno")
    await user_client.put(f"/api/tags/records/note/{note_id}", json={"tag_ids": [winter]})

    assert (
        await user_client.delete(f"/api/vehicles/{vehicle_id}/notes/{note_id}")
    ).status_code in {
        200,
        204,
    }
    purged = await user_client.delete(f"/api/trash/note/{note_id}")
    assert purged.status_code == 204

    # The tag survives; only its use by the purged note is gone.
    remaining = await user_client.get("/api/tags")
    assert [tag["record_count"] for tag in remaining.json()] == [0]
