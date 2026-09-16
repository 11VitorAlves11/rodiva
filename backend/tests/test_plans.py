from datetime import date, timedelta

from httpx import AsyncClient


async def _vehicle(client: AsyncClient, name: str = "Carro de teste") -> str:
    response = await client.post("/api/vehicles", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def test_plan_crud_and_stage_changes(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans",
        json={
            "kind": "maintenance",
            "description": "Trocar correia",
            "priority": "high",
            "estimated_cost": "450.00",
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert created.status_code == 201
    assert created.json()["stage"] == "planned"
    plan_id = created.json()["id"]

    updated = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/plans/{plan_id}",
        json={"stage": "in_progress", "notes": "Peças encomendadas"},
    )
    assert updated.status_code == 200
    assert updated.json()["stage"] == "in_progress"
    assert updated.json()["notes"] == "Peças encomendadas"

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/plans")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [plan_id]

    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/plans/{plan_id}")
    assert deleted.status_code == 204


async def test_completing_plan_atomically_creates_work_and_odometer(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans",
        json={
            "kind": "repair",
            "description": "Substituir bateria",
            "estimated_cost": "120.00",
            "notes": "Plano original",
        },
    )
    plan_id = created.json()["id"]

    completed = await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans/{plan_id}/complete",
        json={"recorded_on": date.today().isoformat(), "odometer_reading": 52_000},
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["stage"] == "completed"
    assert body["completed_work_record_id"] is not None

    work = await user_client.get(f"/api/vehicles/{vehicle_id}/work-records")
    assert work.status_code == 200
    record = next(item for item in work.json() if item["id"] == body["completed_work_record_id"])
    assert record["kind"] == "repair"
    assert record["description"] == "Substituir bateria"
    assert record["total_cost"] == "120.00"
    assert record["notes"] == "Plano original"

    readings = await user_client.get(f"/api/vehicles/{vehicle_id}/odometer-readings")
    assert readings.status_code == 200
    assert any(item["reading"] == 52_000 for item in readings.json())

    repeated = await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans/{plan_id}/complete",
        json={"recorded_on": date.today().isoformat(), "odometer_reading": 52_000},
    )
    assert repeated.status_code == 409


async def test_completed_plan_cannot_be_moved_or_deleted(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans",
        json={"kind": "modification", "description": "Jantes novas"},
    )
    plan_id = created.json()["id"]
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans/{plan_id}/complete",
        json={"recorded_on": date.today().isoformat(), "odometer_reading": 10_000},
    )

    moved = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/plans/{plan_id}", json={"stage": "planned"}
    )
    assert moved.status_code == 409
    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/plans/{plan_id}")
    assert deleted.status_code == 409


async def test_completing_plan_requisitions_inventory_atomically(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    item = await user_client.post(
        "/api/inventory",
        json={"name": "Óleo 5W30", "quantity": "5.000", "unit": "L"},
    )
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans",
        json={"kind": "maintenance", "description": "Mudar óleo"},
    )
    completed = await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans/{created.json()['id']}/complete",
        json={
            "recorded_on": date.today().isoformat(),
            "odometer_reading": 20_000,
            "inventory_items": [{"item_id": item.json()["id"], "quantity": "4.000"}],
        },
    )
    assert completed.status_code == 200
    inventory = await user_client.get("/api/inventory")
    assert inventory.json()[0]["quantity"] == "1.000"
    movements = await user_client.get(f"/api/inventory/{item.json()['id']}/movements")
    requisition = next(entry for entry in movements.json() if entry["kind"] == "requisition")
    assert requisition["plan_id"] == created.json()["id"]
    assert requisition["work_record_id"] == completed.json()["completed_work_record_id"]
