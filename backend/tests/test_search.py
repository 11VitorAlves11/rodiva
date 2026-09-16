from datetime import date, timedelta

from httpx import AsyncClient


async def _vehicle(client: AsyncClient, name: str = "Carro de teste") -> str:
    response = await client.post("/api/vehicles", json={"name": name})
    assert response.status_code == 201
    return str(response.json()["id"])


async def test_global_search_is_case_and_accent_insensitive(user_client: AsyncClient) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Citroën Familiar"})).json()
    await user_client.post(
        f"/api/vehicles/{vehicle['id']}/work-records",
        json={
            "recorded_on": "2026-09-01",
            "kind": "repair",
            "description": "Substituição do alternador",
        },
    )
    by_vehicle = await user_client.get("/api/search", params={"q": "CITROEN"})
    assert by_vehicle.status_code == 200
    assert any(
        item["kind"] == "vehicle" and item["id"] == vehicle["id"] for item in by_vehicle.json()
    )
    by_work = await user_client.get("/api/search", params={"q": "substituicao"})
    assert any(item["kind"] == "work" and "alternador" in item["title"] for item in by_work.json())


async def test_global_search_does_not_leak_another_household(
    user_client: AsyncClient, register
) -> None:
    other, _ = await register()
    await other.post("/api/vehicles", json={"name": "Segredo absoluto"})
    response = await user_client.get("/api/search", params={"q": "segredo"})
    assert response.status_code == 200
    assert response.json() == []


async def test_search_without_a_text_term_is_allowed_and_filters_by_kind_and_vehicle(
    user_client: AsyncClient,
) -> None:
    vehicle_a = await _vehicle(user_client, "Veículo A")
    vehicle_b = await _vehicle(user_client, "Veículo B")
    await user_client.post(
        f"/api/vehicles/{vehicle_a}/fuel-records",
        json={"recorded_on": "2026-01-10", "volume_litres": "10", "total_price": "15.00"},
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_b}/notes",
        json={"title": "Nota do B", "content": "conteúdo"},
    )

    only_fuel = await user_client.get("/api/search", params={"kind": "fuel"})
    assert only_fuel.status_code == 200
    assert only_fuel.json() and all(item["kind"] == "fuel" for item in only_fuel.json())

    only_vehicle_b = await user_client.get("/api/search", params={"vehicle_id": vehicle_b})
    assert only_vehicle_b.status_code == 200
    assert all(item["vehicle_id"] == vehicle_b for item in only_vehicle_b.json())
    assert any(item["kind"] == "note" for item in only_vehicle_b.json())
    assert not any(item["kind"] == "fuel" for item in only_vehicle_b.json())


async def test_search_rejects_a_vehicle_id_outside_the_household(user_client: AsyncClient) -> None:
    response = await user_client.get(
        "/api/search", params={"vehicle_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 404


async def test_search_filters_by_date_range(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={"issued_on": "2026-01-05", "category": "insurance", "amount": "100.00"},
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={"issued_on": "2026-06-05", "category": "tax", "amount": "50.00"},
    )

    in_range = await user_client.get(
        "/api/search",
        params={"kind": "expense", "date_from": "2026-01-01", "date_to": "2026-02-01"},
    )
    assert in_range.status_code == 200
    categories = {item["title"] for item in in_range.json()}
    assert categories == {"insurance"}


async def test_search_sort_orders(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={"recorded_on": "2026-01-01", "kind": "repair", "description": "Zebra"},
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={"recorded_on": "2026-03-01", "kind": "repair", "description": "Amora"},
    )

    ascending = await user_client.get(
        "/api/search", params={"kind": "work", "sort": "occurred_on_asc"}
    )
    dates = [item["occurred_on"] for item in ascending.json()]
    assert dates == sorted(dates)

    title_asc = await user_client.get("/api/search", params={"kind": "work", "sort": "title_asc"})
    titles = [item["title"] for item in title_asc.json()]
    assert titles == ["Amora", "Zebra"]

    title_desc = await user_client.get("/api/search", params={"kind": "work", "sort": "title_desc"})
    titles_desc = [item["title"] for item in title_desc.json()]
    assert titles_desc == ["Zebra", "Amora"]


async def test_saved_view_crud_and_household_isolation(user_client: AsyncClient, register) -> None:
    created = await user_client.post(
        "/api/search/saved-views",
        json={
            "name": "Custos de janeiro",
            "query": {"kind": ["expense"], "date_from": "2026-01-01"},
        },
    )
    assert created.status_code == 201
    view_id = created.json()["id"]

    listed = await user_client.get("/api/search/saved-views")
    assert listed.status_code == 200
    assert any(item["id"] == view_id for item in listed.json())

    other, _ = await register()
    other_listed = await other.get("/api/search/saved-views")
    assert other_listed.json() == []
    other_delete = await other.delete(f"/api/search/saved-views/{view_id}")
    assert other_delete.status_code == 404

    deleted = await user_client.delete(f"/api/search/saved-views/{view_id}")
    assert deleted.status_code == 204
    listed_again = await user_client.get("/api/search/saved-views")
    assert listed_again.json() == []


async def test_bulk_delete_success_and_partial_failure_from_another_household(
    user_client: AsyncClient, register
) -> None:
    vehicle_id = await _vehicle(user_client)
    note = (
        await user_client.post(
            f"/api/vehicles/{vehicle_id}/notes",
            json={"title": "Para eliminar", "content": "conteúdo"},
        )
    ).json()

    other, _ = await register()
    other_vehicle = await _vehicle(other, "Veículo alheio")
    other_note = (
        await other.post(
            f"/api/vehicles/{other_vehicle}/notes",
            json={"title": "Nota alheia", "content": "conteúdo"},
        )
    ).json()

    response = await user_client.post(
        "/api/search/bulk",
        json={
            "operation": "delete",
            "items": [
                {"kind": "note", "id": note["id"]},
                {"kind": "note", "id": other_note["id"]},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requested"] == 2
    assert body["succeeded"] == 1
    assert len(body["failures"]) == 1
    assert body["failures"][0]["id"] == other_note["id"]
    assert body["failures"][0]["reason"]

    remaining = await user_client.get(f"/api/vehicles/{vehicle_id}/notes")
    assert remaining.json() == []
    other_remaining = await other.get(f"/api/vehicles/{other_vehicle}/notes")
    assert len(other_remaining.json()) == 1


async def test_bulk_duplicate_resets_inventory_stock_and_equipment_state(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    equipment = (
        await user_client.post(
            f"/api/vehicles/{vehicle_id}/equipment",
            json={"name": "Pneus", "kind": "tires"},
        )
    ).json()
    item = (
        await user_client.post(
            "/api/inventory",
            json={"name": "Óleo", "quantity": "5.000", "unit": "L"},
        )
    ).json()

    response = await user_client.post(
        "/api/search/bulk",
        json={
            "operation": "duplicate",
            "items": [
                {"kind": "equipment", "id": equipment["id"]},
                {"kind": "inventory", "id": item["id"]},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["succeeded"] == 2
    assert body["failures"] == []

    equipment_list = (await user_client.get(f"/api/vehicles/{vehicle_id}/equipment")).json()
    assert len(equipment_list) == 2
    assert all(entry["status"] != "mounted" for entry in equipment_list)

    inventory_list = (await user_client.get("/api/inventory")).json()
    duplicated_item = next(entry for entry in inventory_list if entry["id"] != item["id"])
    assert duplicated_item["quantity"] == "0.000"


async def test_bulk_move_changes_the_vehicle(user_client: AsyncClient) -> None:
    vehicle_a = await _vehicle(user_client, "Origem")
    vehicle_b = await _vehicle(user_client, "Destino")
    note = (
        await user_client.post(
            f"/api/vehicles/{vehicle_a}/notes",
            json={"title": "Para mover", "content": "conteúdo"},
        )
    ).json()

    response = await user_client.post(
        "/api/search/bulk",
        json={
            "operation": "move",
            "items": [{"kind": "note", "id": note["id"]}],
            "target_vehicle_id": vehicle_b,
        },
    )
    assert response.status_code == 200
    assert response.json()["succeeded"] == 1

    assert (await user_client.get(f"/api/vehicles/{vehicle_a}/notes")).json() == []
    moved = (await user_client.get(f"/api/vehicles/{vehicle_b}/notes")).json()
    assert len(moved) == 1
    assert moved[0]["id"] == note["id"]


async def test_bulk_edit_requires_a_single_shared_kind(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    work = (
        await user_client.post(
            f"/api/vehicles/{vehicle_id}/work-records",
            json={"recorded_on": "2026-01-01", "kind": "repair", "description": "A"},
        )
    ).json()
    note = (
        await user_client.post(
            f"/api/vehicles/{vehicle_id}/notes",
            json={"title": "B", "content": "conteúdo"},
        )
    ).json()

    mixed = await user_client.post(
        "/api/search/bulk",
        json={
            "operation": "edit",
            "items": [
                {"kind": "work", "id": work["id"]},
                {"kind": "note", "id": note["id"]},
            ],
            "fields": {"kind": "maintenance"},
        },
    )
    assert mixed.status_code == 422


async def test_bulk_edit_applies_the_update_schema_to_every_item(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    first = (
        await user_client.post(
            f"/api/vehicles/{vehicle_id}/work-records",
            json={"recorded_on": "2026-01-01", "kind": "repair", "description": "A"},
        )
    ).json()
    second = (
        await user_client.post(
            f"/api/vehicles/{vehicle_id}/work-records",
            json={"recorded_on": "2026-01-02", "kind": "repair", "description": "B"},
        )
    ).json()

    response = await user_client.post(
        "/api/search/bulk",
        json={
            "operation": "edit",
            "items": [
                {"kind": "work", "id": first["id"]},
                {"kind": "work", "id": second["id"]},
            ],
            "fields": {"kind": "maintenance"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["succeeded"] == 2

    records = (await user_client.get(f"/api/vehicles/{vehicle_id}/work-records")).json()
    assert all(record["kind"] == "maintenance" for record in records)

    invalid_field = await user_client.post(
        "/api/search/bulk",
        json={
            "operation": "edit",
            "items": [{"kind": "work", "id": first["id"]}],
            "fields": {"kind": "not-a-real-kind"},
        },
    )
    assert invalid_field.status_code == 422


async def test_bulk_export_returns_csv(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    note = (
        await user_client.post(
            f"/api/vehicles/{vehicle_id}/notes",
            json={"title": "Nota exportável", "content": "conteúdo"},
        )
    ).json()

    response = await user_client.post(
        "/api/search/bulk",
        json={"operation": "export", "items": [{"kind": "note", "id": note["id"]}]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text.lstrip("﻿")
    lines = body.strip().splitlines()
    assert lines[0] == "kind,title,subtitle,vehicle,occurred_on,url"
    assert len(lines) == 2
    assert "Nota exportável" in lines[1]


async def test_bulk_operations_reject_disallowed_kinds(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)

    delete_vehicle = await user_client.post(
        "/api/search/bulk",
        json={"operation": "delete", "items": [{"kind": "vehicle", "id": vehicle_id}]},
    )
    assert delete_vehicle.status_code == 200
    body = delete_vehicle.json()
    assert body["succeeded"] == 0
    assert body["failures"][0]["kind"] == "vehicle"


async def test_search_supports_a_past_date_range(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/notes",
        json={"title": "Antiga", "content": "conteúdo"},
    )
    response = await user_client.get(
        "/api/search", params={"kind": "note", "date_from": "2000-01-01", "date_to": yesterday}
    )
    assert response.status_code == 200
    assert response.json() == []
