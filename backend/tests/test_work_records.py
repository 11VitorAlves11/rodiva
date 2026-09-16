from httpx import AsyncClient


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_work_record_logs_an_odometer_reading(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)

    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={
            "recorded_on": "2026-02-01",
            "kind": "maintenance",
            "description": "Mudança de óleo e filtros",
            "odometer_reading": 20_000,
            "total_cost": "120.00",
            "supplier": "Oficina do Zé",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["kind"] == "maintenance"
    assert body["total_cost"] == "120.00"

    readings = await user_client.get(f"/api/vehicles/{vehicle_id}/odometer-readings")
    assert readings.status_code == 200
    assert readings.json()[0]["reading"] == 20_000
    assert readings.json()[0]["notes"] == (
        "Leitura criada automaticamente a partir de uma intervenção"
    )


async def test_list_work_records_orders_most_recent_first(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    for recorded_on, description in (
        ("2026-01-05", "Primeira intervenção"),
        ("2026-02-10", "Segunda intervenção"),
    ):
        response = await user_client.post(
            f"/api/vehicles/{vehicle_id}/work-records",
            json={"recorded_on": recorded_on, "kind": "repair", "description": description},
        )
        assert response.status_code == 201

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/work-records")
    assert listed.status_code == 200
    assert [item["description"] for item in listed.json()] == [
        "Segunda intervenção",
        "Primeira intervenção",
    ]


async def test_update_and_delete_work_record(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={"recorded_on": "2026-01-05", "kind": "repair", "description": "Travões"},
    )
    record_id = created.json()["id"]

    updated = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/work-records/{record_id}",
        json={"total_cost": "89.90", "supplier": "Oficina Central"},
    )
    assert updated.status_code == 200
    assert updated.json()["total_cost"] == "89.90"
    assert updated.json()["supplier"] == "Oficina Central"
    assert updated.json()["description"] == "Travões"

    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/work-records/{record_id}")
    assert deleted.status_code == 204

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/work-records")
    assert listed.json() == []


async def test_deleting_work_record_restores_requisitioned_stock(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    record = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={"recorded_on": "2026-01-05", "kind": "maintenance", "description": "Filtros"},
    )
    record_id = record.json()["id"]

    item = await user_client.post(
        "/api/inventory",
        json={"name": "Filtro de óleo", "unit": "unit", "quantity": "5.000"},
    )
    item_id = item.json()["id"]
    await user_client.post(
        f"/api/inventory/{item_id}/movements",
        json={"kind": "requisition", "quantity": "2.000", "work_record_id": record_id},
    )
    after_requisition = await user_client.get("/api/inventory")
    assert after_requisition.json()[0]["quantity"] == "3.000"

    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/work-records/{record_id}")
    assert deleted.status_code == 204

    restored = await user_client.get("/api/inventory")
    assert restored.json()[0]["quantity"] == "5.000"

    movements = await user_client.get(f"/api/inventory/{item_id}/movements")
    kinds = [entry["kind"] for entry in movements.json()]
    assert kinds.count("return") == 1
    return_movement = next(entry for entry in movements.json() if entry["kind"] == "return")
    assert return_movement["quantity_delta"] == "2.000"
    assert return_movement["work_record_id"] is None
