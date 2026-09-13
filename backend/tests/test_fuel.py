from httpx import AsyncClient


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert response.status_code == 201
    return response.json()["id"]


async def test_fuel_calculates_unit_price_and_full_tank_consumption(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    first = await user_client.post(
        f"/api/vehicles/{vehicle_id}/fuel-records",
        json={
            "recorded_on": "2026-01-10",
            "odometer_reading": 10_000,
            "volume_litres": "45.000",
            "total_price": "76.50",
            "full_tank": True,
        },
    )
    assert first.status_code == 201
    assert first.json()["unit_price"] == "1.700"
    assert first.json()["consumption_l_per_100km"] is None

    second = await user_client.post(
        f"/api/vehicles/{vehicle_id}/fuel-records",
        json={
            "recorded_on": "2026-01-20",
            "odometer_reading": 10_600,
            "volume_litres": "42.700",
            "total_price": "73.10",
            "full_tank": True,
        },
    )
    assert second.status_code == 201
    assert second.json()["unit_price"] == "1.712"
    assert second.json()["consumption_l_per_100km"] == "7.117"

    readings = await user_client.get(f"/api/vehicles/{vehicle_id}/odometer-readings")
    assert readings.status_code == 200
    assert [item["reading"] for item in readings.json()] == [10_600, 10_000]
