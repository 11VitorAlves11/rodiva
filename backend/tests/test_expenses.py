from httpx import AsyncClient


async def test_create_and_list_expense(user_client: AsyncClient) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carro"})
    vehicle_id = vehicle.json()["id"]
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={"issued_on": "2026-09-13", "category": "insurance", "amount": "320.50"},
    )
    assert created.status_code == 201
    assert created.json()["amount"] == "320.50"
    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/expenses")
    assert listed.status_code == 200
    assert listed.json()[0]["category"] == "insurance"


async def test_update_and_delete_expense(user_client: AsyncClient) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carro"})
    vehicle_id = vehicle.json()["id"]
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": "2026-09-13",
            "category": "tax",
            "amount": "120.00",
            "status": "pending",
        },
    )
    expense_id = created.json()["id"]

    updated = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/expenses/{expense_id}", json={"status": "paid"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "paid"
    assert updated.json()["amount"] == "120.00"

    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/expenses/{expense_id}")
    assert deleted.status_code == 204

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/expenses")
    assert listed.json() == []
