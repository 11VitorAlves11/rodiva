from httpx import AsyncClient


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert response.status_code == 201
    return response.json()["id"]


async def test_readings_calculate_distance_and_recalculate_in_date_order(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)

    first = await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-10", "reading": 10_000},
    )
    assert first.status_code == 201
    assert first.json()["distance"] is None

    latest = await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-20", "reading": 10_500},
    )
    assert latest.status_code == 201
    assert latest.json()["distance"] == 500

    inserted = await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-15", "reading": 10_200},
    )
    assert inserted.status_code == 201
    assert inserted.json()["distance"] == 200

    history = await user_client.get(f"/api/vehicles/{vehicle_id}/odometer-readings")
    assert history.status_code == 200
    assert [item["distance"] for item in history.json()] == [300, 200, None]


async def test_lower_reading_requires_a_documented_adjustment(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-10", "reading": 10_000},
    )

    invalid = await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-11", "reading": 9_000},
    )
    assert invalid.status_code == 422

    adjusted = await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-11", "reading": 9_000, "is_adjustment": True},
    )
    assert adjusted.status_code == 201
    assert adjusted.json()["distance"] is None


async def test_editing_a_reading_recalculates_its_successor(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    first = await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-10", "reading": 10_000},
    )
    second = await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-20", "reading": 10_500},
    )
    assert first.status_code == 201 and second.status_code == 201

    changed = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/odometer-readings/{first.json()['id']}",
        json={"reading": 10_100},
    )
    assert changed.status_code == 200
    history = await user_client.get(f"/api/vehicles/{vehicle_id}/odometer-readings")
    assert history.status_code == 200
    assert history.json()[0]["distance"] == 400
