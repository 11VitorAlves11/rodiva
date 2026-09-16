from httpx import AsyncClient


async def test_inventory_tracks_movements_and_prevents_negative_stock(
    user_client: AsyncClient,
) -> None:
    created = await user_client.post(
        "/api/inventory",
        json={
            "name": "Filtro de óleo",
            "reference": "ABC-123",
            "quantity": "2.000",
            "unit": "un",
            "unit_cost": "8.50",
            "minimum_quantity": "1.000",
        },
    )
    assert created.status_code == 201
    item_id = created.json()["id"]
    assert created.json()["quantity"] == "2.000"
    assert created.json()["low_stock"] is False

    used = await user_client.post(
        f"/api/inventory/{item_id}/movements",
        json={"kind": "requisition", "quantity": "1.000", "notes": "Revisão"},
    )
    assert used.status_code == 201
    assert used.json()["quantity_delta"] == "-1.000"
    assert used.json()["quantity_after"] == "1.000"

    listed = await user_client.get("/api/inventory")
    assert listed.status_code == 200
    assert listed.json()[0]["low_stock"] is True

    rejected = await user_client.post(
        f"/api/inventory/{item_id}/movements",
        json={"kind": "requisition", "quantity": "2.000"},
    )
    assert rejected.status_code == 409

    movements = await user_client.get(f"/api/inventory/{item_id}/movements")
    assert movements.status_code == 200
    assert len(movements.json()) == 2


async def test_inventory_item_can_be_vehicle_specific_and_requires_zero_to_delete(
    user_client: AsyncClient,
) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carro"})
    created = await user_client.post(
        "/api/inventory",
        json={"name": "Lâmpada", "vehicle_id": vehicle.json()["id"], "quantity": "1"},
    )
    item_id = created.json()["id"]
    assert (await user_client.delete(f"/api/inventory/{item_id}")).status_code == 409
    removed = await user_client.post(
        f"/api/inventory/{item_id}/movements",
        json={"kind": "removal", "quantity": "1"},
    )
    assert removed.status_code == 201
    assert (await user_client.delete(f"/api/inventory/{item_id}")).status_code == 204
