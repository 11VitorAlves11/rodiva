from datetime import date, timedelta

from httpx import AsyncClient

from tests.conftest import RegisterFn


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/v1/vehicles", json={"name": "Golf", "distance_unit": "km"})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _note(client: AsyncClient, vehicle_id: str) -> str:
    response = await client.post(
        f"/api/v1/vehicles/{vehicle_id}/notes",
        json={"title": "Chave suplente", "content": "Na gaveta"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def test_a_deleted_record_leaves_the_listing_and_lands_in_the_bin(
    register: RegisterFn,
) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    note_id = await _note(client, vehicle_id)

    assert (
        await client.delete(f"/api/v1/vehicles/{vehicle_id}/notes/{note_id}")
    ).status_code == 204
    assert (await client.get(f"/api/v1/vehicles/{vehicle_id}/notes")).json() == []
    # It is gone from the record's own endpoint too, not just the listing.
    assert (await client.get(f"/api/v1/vehicles/{vehicle_id}/notes")).status_code == 200

    trash = (await client.get("/api/v1/trash")).json()
    assert [(item["entity_type"], item["entity_id"]) for item in trash] == [("note", note_id)]
    assert trash[0]["summary"] == "Chave suplente"
    assert trash[0]["deleted_by_label"]


async def test_restoring_puts_the_record_back(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    note_id = await _note(client, vehicle_id)
    await client.delete(f"/api/v1/vehicles/{vehicle_id}/notes/{note_id}")

    assert (await client.post(f"/api/v1/trash/note/{note_id}/restore")).status_code == 204
    notes = (await client.get(f"/api/v1/vehicles/{vehicle_id}/notes")).json()
    assert [note["id"] for note in notes] == [note_id]
    assert (await client.get("/api/v1/trash")).json() == []


async def test_deleting_a_fuel_record_rebuilds_consumption_and_restoring_puts_it_back(
    register: RegisterFn,
) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    today = date.today()
    ids = []
    for offset, reading, litres in ((30, 10_000, 40), (20, 10_500, 35), (10, 11_000, 42)):
        response = await client.post(
            f"/api/v1/vehicles/{vehicle_id}/fuel-records",
            json={
                "recorded_on": (today - timedelta(days=offset)).isoformat(),
                "odometer_reading": reading,
                "volume_litres": litres,
                "total_price": 70,
                "full_tank": True,
            },
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])

    before = (await client.get(f"/api/v1/vehicles/{vehicle_id}/fuel-records")).json()
    last_consumption = next(row["consumption_l_per_100km"] for row in before if row["id"] == ids[2])
    assert last_consumption is not None

    # Removing the middle fill-up makes the last one span a longer distance.
    await client.delete(f"/api/v1/vehicles/{vehicle_id}/fuel-records/{ids[1]}")
    during = (await client.get(f"/api/v1/vehicles/{vehicle_id}/fuel-records")).json()
    assert len(during) == 2
    assert next(row["consumption_l_per_100km"] for row in during if row["id"] == ids[2]) != (
        last_consumption
    )

    assert (await client.post(f"/api/v1/trash/fuel_record/{ids[1]}/restore")).status_code == 204
    after = (await client.get(f"/api/v1/vehicles/{vehicle_id}/fuel-records")).json()
    assert len(after) == 3
    assert next(row["consumption_l_per_100km"] for row in after if row["id"] == ids[2]) == (
        last_consumption
    )


async def test_a_deleted_record_stays_out_of_search_and_reports(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    note_id = await _note(client, vehicle_id)

    found = (await client.get("/api/v1/search?q=suplente")).json()
    assert any(item["id"] == note_id for item in found)

    await client.delete(f"/api/v1/vehicles/{vehicle_id}/notes/{note_id}")
    found = (await client.get("/api/v1/search?q=suplente")).json()
    assert not any(item["id"] == note_id for item in found)


async def test_purging_is_final_and_owner_only(register: RegisterFn) -> None:
    owner, _ = await register()
    member, _ = await register()
    invite = (await owner.post("/api/household/invites", json={"role": "editor"})).json()
    await member.post(f"/auth/invites/{invite['token']}/accept")

    vehicle_id = await _vehicle(owner)
    note_id = await _note(owner, vehicle_id)
    await owner.delete(f"/api/v1/vehicles/{vehicle_id}/notes/{note_id}")

    # An editor may put a record back but not destroy it.
    assert (await member.delete(f"/api/v1/trash/note/{note_id}")).status_code == 403
    assert (await owner.delete(f"/api/v1/trash/note/{note_id}")).status_code == 204
    assert (await owner.get("/api/v1/trash")).json() == []
    assert (await owner.post(f"/api/v1/trash/note/{note_id}/restore")).status_code == 404


async def test_the_bin_is_scoped_to_the_household(register: RegisterFn) -> None:
    owner, _ = await register()
    other, _ = await register()
    vehicle_id = await _vehicle(owner)
    note_id = await _note(owner, vehicle_id)
    await owner.delete(f"/api/v1/vehicles/{vehicle_id}/notes/{note_id}")

    assert (await other.get("/api/v1/trash")).json() == []
    assert (await other.post(f"/api/v1/trash/note/{note_id}/restore")).status_code == 404
    assert (await other.delete(f"/api/v1/trash/note/{note_id}")).status_code == 404


async def test_a_record_cannot_be_restored_before_its_vehicle(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    note_id = await _note(client, vehicle_id)
    await client.delete(f"/api/v1/vehicles/{vehicle_id}/notes/{note_id}")
    await client.delete(f"/api/v1/vehicles/{vehicle_id}")

    conflict = await client.post(f"/api/v1/trash/note/{note_id}/restore")
    assert conflict.status_code == 409

    assert (await client.post(f"/api/v1/trash/vehicle/{vehicle_id}/restore")).status_code == 204
    assert (await client.post(f"/api/v1/trash/note/{note_id}/restore")).status_code == 204
    assert len((await client.get(f"/api/v1/vehicles/{vehicle_id}/notes")).json()) == 1


async def test_deletions_and_restores_reach_the_audit_trail(register: RegisterFn) -> None:
    client, _ = await register()
    vehicle_id = await _vehicle(client)
    note_id = await _note(client, vehicle_id)
    await client.delete(f"/api/v1/vehicles/{vehicle_id}/notes/{note_id}")
    await client.post(f"/api/v1/trash/note/{note_id}/restore")

    events = (await client.get("/api/v1/audit?action=record")).json()["items"]
    assert [event["action"] for event in events] == ["record.restored", "record.deleted"]
    assert events[0]["entity_type"] == "note"
    assert events[1]["context"]["vehicle_id"] == vehicle_id
