from datetime import date, timedelta

from httpx import AsyncClient

from tests.conftest import RegisterFn


async def test_tires_mount_distance_rotation_and_unmount(user_client: AsyncClient) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carro"})
    vehicle_id = vehicle.json()["id"]
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment",
        json={
            "name": "Pneus de verão",
            "kind": "tires",
            "manufacturer": "Continental",
            "tire_size": "225/45 R17",
            "tire_dot": "1226",
            "tread_depth_mm": "7.50",
            "season": "summer",
        },
    )
    assert created.status_code == 201
    equipment_id = created.json()["id"]

    today = date.today()
    mounted = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/mount",
        json={
            "on": today.isoformat(),
            "odometer": 1_000,
            "positions": {"front_left": "A", "front_right": "B"},
        },
    )
    assert mounted.status_code == 201
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": today.isoformat(), "reading": 1_000},
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": (today + timedelta(days=1)).isoformat(), "reading": 1_250},
    )
    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/equipment")
    assert listed.json()[0]["distance_accumulated"] == 250

    rotated = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/rotate",
        json={
            "on": (today + timedelta(days=1)).isoformat(),
            "odometer": 1_250,
            "positions": {"front_left": "B", "front_right": "A"},
        },
    )
    assert rotated.status_code == 201

    unmounted = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/unmount",
        json={"on": (today + timedelta(days=2)).isoformat(), "odometer": 1_300},
    )
    assert unmounted.status_code == 200
    assert unmounted.json()["distance"] == 300
    history = await user_client.get(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/rotations"
    )
    assert len(history.json()) == 1


async def test_non_tire_or_unmounted_equipment_cannot_rotate(
    user_client: AsyncClient,
) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carrinha"})
    item = await user_client.post(
        f"/api/vehicles/{vehicle.json()['id']}/equipment",
        json={"name": "Barras", "kind": "roof_rack"},
    )
    response = await user_client.post(
        f"/api/vehicles/{vehicle.json()['id']}/equipment/{item.json()['id']}/rotate",
        json={"on": date.today().isoformat(), "odometer": 10, "positions": {"left": "right"}},
    )
    assert response.status_code == 409


async def test_create_and_list_equipment_reminder(user_client: AsyncClient) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carro"})
    vehicle_id = vehicle.json()["id"]
    item = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment",
        json={"name": "Pneus de inverno", "kind": "tires"},
    )
    equipment_id = item.json()["id"]

    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders",
        json={"title": "Rodar pneus", "due_odometer": 10_000},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["vehicle_id"] == vehicle_id
    assert body["equipment_id"] == equipment_id

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [body["id"]]

    equipment_list = await user_client.get(f"/api/vehicles/{vehicle_id}/equipment")
    assert equipment_list.json()[0]["open_reminders_count"] == 1

    vehicle_reminders = await user_client.get(f"/api/vehicles/{vehicle_id}/reminders")
    assert any(r["id"] == body["id"] for r in vehicle_reminders.json())


async def test_complete_and_delete_equipment_reminder_via_generic_endpoints(
    user_client: AsyncClient,
) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carro"})
    vehicle_id = vehicle.json()["id"]
    item = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment",
        json={"name": "Reboque", "kind": "trailer"},
    )
    equipment_id = item.json()["id"]

    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders",
        json={"title": "Verificar matrícula", "due_date": date.today().isoformat()},
    )
    reminder_id = created.json()["id"]

    completed = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/complete"
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}")
    assert deleted.status_code == 204

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders")
    assert all(r["id"] != reminder_id for r in listed.json())


async def test_repeating_equipment_reminder_keeps_equipment_link_on_renewal(
    user_client: AsyncClient,
) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carro"})
    vehicle_id = vehicle.json()["id"]
    item = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment",
        json={"name": "Pneus", "kind": "tires"},
    )
    equipment_id = item.json()["id"]

    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders",
        json={"title": "Rodar pneus", "due_odometer": 10_000, "repeat_distance": 10_000},
    )
    reminder_id = created.json()["id"]

    await user_client.post(f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/complete")

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders")
    renewed = next(r for r in listed.json() if r["status"] != "completed")
    assert renewed["equipment_id"] == equipment_id


async def test_equipment_reminder_is_isolated_per_household(register: RegisterFn) -> None:
    client_a, _ = await register(household_name="Household A")
    client_b, _ = await register(household_name="Household B")

    vehicle = await client_a.post("/api/vehicles", json={"name": "Carro A"})
    vehicle_id = vehicle.json()["id"]
    item = await client_a.post(
        f"/api/vehicles/{vehicle_id}/equipment",
        json={"name": "Pneus", "kind": "tires"},
    )
    equipment_id = item.json()["id"]
    created = await client_a.post(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders",
        json={"title": "Rodar pneus", "due_odometer": 10_000},
    )
    reminder_id = created.json()["id"]

    other_vehicle = await client_b.get(f"/api/vehicles/{vehicle_id}")
    assert other_vehicle.status_code == 404

    other_equipment_reminders = await client_b.get(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders"
    )
    assert other_equipment_reminders.status_code == 404

    other_create = await client_b.post(
        f"/api/vehicles/{vehicle_id}/equipment/{equipment_id}/reminders",
        json={"title": "Não devia funcionar", "due_odometer": 5_000},
    )
    assert other_create.status_code == 404

    other_complete = await client_b.post(
        f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/complete"
    )
    assert other_complete.status_code == 404

    other_delete = await client_b.delete(f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}")
    assert other_delete.status_code == 404
