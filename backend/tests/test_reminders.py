from datetime import date, timedelta

from httpx import AsyncClient


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert response.status_code == 201
    return response.json()["id"]


async def test_reminder_requires_a_due_date_or_odometer(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders", json={"title": "Sem prazo"}
    )
    assert response.status_code == 422


async def test_reminders_are_urgency_ranked_and_sorted(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    today = date.today()
    plans = {
        "Revisão futura": today + timedelta(days=120),
        "Revisão a aproximar-se": today + timedelta(days=60),
        "Revisão urgente": today + timedelta(days=15),
        "Revisão muito urgente": today + timedelta(days=3),
        "Revisão atrasada": today - timedelta(days=1),
    }
    for title, due_date in plans.items():
        response = await user_client.post(
            f"/api/vehicles/{vehicle_id}/reminders",
            json={"title": title, "due_date": due_date.isoformat()},
        )
        assert response.status_code == 201

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/reminders")
    assert listed.status_code == 200
    body = listed.json()
    assert [item["title"] for item in body] == [
        "Revisão atrasada",
        "Revisão muito urgente",
        "Revisão urgente",
        "Revisão a aproximar-se",
        "Revisão futura",
    ]
    assert [item["urgency"] for item in body] == [
        "overdue",
        "very_urgent",
        "urgent",
        "upcoming",
        "future",
    ]


async def test_completing_a_reminder_marks_it_completed(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders",
        json={"title": "Trocar pneus", "due_odometer": 50_000},
    )
    assert created.status_code == 201
    reminder_id = created.json()["id"]

    completed = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/complete"
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["urgency"] == "completed"
    assert completed.json()["completed_at"] is not None


async def test_completing_a_repeating_reminder_renews_it(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": date.today().isoformat(), "reading": 40_000},
    )
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders",
        json={
            "title": "Mudança de óleo",
            "due_odometer": 45_000,
            "repeat_days": 180,
            "repeat_distance": 10_000,
        },
    )
    reminder_id = created.json()["id"]

    completed = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/complete"
    )
    assert completed.status_code == 200

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/reminders")
    titles = [item for item in listed.json() if item["title"] == "Mudança de óleo"]
    assert len(titles) == 2
    renewed = next(item for item in titles if item["status"] != "completed")
    assert renewed["due_date"] == (date.today() + timedelta(days=180)).isoformat()
    assert renewed["due_odometer"] == 50_000


async def test_completing_a_non_repeating_reminder_does_not_renew_it(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders",
        json={"title": "Inspeção", "due_odometer": 60_000},
    )
    reminder_id = created.json()["id"]

    await user_client.post(f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/complete")

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/reminders")
    assert len([item for item in listed.json() if item["title"] == "Inspeção"]) == 1


async def test_reminder_can_be_updated_reopened_and_deleted(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders",
        json={"title": "Seguro", "due_date": date.today().isoformat()},
    )
    reminder_id = created.json()["id"]

    updated = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}",
        json={"title": "Renovar seguro", "due_odometer": 80_000, "notes": "Comparar preços"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renovar seguro"
    assert updated.json()["due_odometer"] == 80_000
    assert updated.json()["notes"] == "Comparar preços"

    await user_client.post(f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/complete")
    reopened = await user_client.post(f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}/reopen")
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "active"
    assert reopened.json()["completed_at"] is None

    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/reminders/{reminder_id}")
    assert deleted.status_code == 204
    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/reminders")
    assert all(item["id"] != reminder_id for item in listed.json())


async def test_reminder_update_cannot_clear_all_due_conditions(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders",
        json={"title": "IPO", "due_date": date.today().isoformat()},
    )
    response = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/reminders/{created.json()['id']}",
        json={"due_date": None},
    )
    assert response.status_code == 422
