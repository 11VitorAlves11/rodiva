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
