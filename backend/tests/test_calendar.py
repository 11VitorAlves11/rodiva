from datetime import date

from httpx import AsyncClient


async def test_revocable_calendar_feed_combines_preventive_events(
    user_client: AsyncClient,
) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carrinha"})
    vehicle_id = vehicle.json()["id"]
    today = date.today().isoformat()
    reminder = await user_client.post(
        f"/api/vehicles/{vehicle_id}/reminders",
        json={"title": "Trocar o óleo, filtro", "due_date": today},
    )
    assert reminder.status_code == 201
    expense = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": today,
            "category": "insurance",
            "amount": "100.00",
            "status": "pending",
        },
    )
    assert expense.status_code == 201
    plan = await user_client.post(
        f"/api/vehicles/{vehicle_id}/plans",
        json={"kind": "maintenance", "description": "Revisão anual", "due_date": today},
    )
    assert plan.status_code == 201

    initial = await user_client.get("/api/calendar-feed")
    assert initial.status_code == 200
    assert initial.json() == {"active": False, "created_at": None}

    created = await user_client.post("/api/calendar-feed")
    assert created.status_code == 201
    assert created.json()["active"] is True
    assert created.json()["feed_path"] == f"/api/calendar/{created.json()['token']}.ics"

    calendar = await user_client.get(created.json()["feed_path"])
    assert calendar.status_code == 200
    assert calendar.headers["content-type"].startswith("text/calendar")
    assert "BEGIN:VCALENDAR" in calendar.text
    assert "Trocar o óleo\\, filtro" in calendar.text
    assert "insurance" in calendar.text
    assert "Revisão anual" in calendar.text
    assert "Carrinha" in calendar.text

    revoked = await user_client.delete("/api/calendar-feed")
    assert revoked.status_code == 204
    unavailable = await user_client.get(created.json()["feed_path"])
    assert unavailable.status_code == 404


async def test_creating_new_feed_revokes_previous_token(user_client: AsyncClient) -> None:
    first = await user_client.post("/api/calendar-feed")
    second = await user_client.post("/api/calendar-feed")
    assert first.json()["token"] != second.json()["token"]
    assert (await user_client.get(first.json()["feed_path"])).status_code == 404
    assert (await user_client.get(second.json()["feed_path"])).status_code == 200
