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
