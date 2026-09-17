"""The fields the spec asks of vehicles, work records and expenses.

Covers RF-VEI-005/006/007/008/012, RF-INT-002/003/009 and RF-DES-002/004/005/007.
"""

from datetime import date, timedelta
from decimal import Decimal

from httpx import AsyncClient

from app.services.recurrence import next_occurrence_date


async def _vehicle(client: AsyncClient, **extra: object) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste", **extra})
    assert response.status_code == 201, response.text
    return response.json()["id"]


# --- vehicle ---------------------------------------------------------------


async def test_a_vehicle_records_energy_ownership_and_odometer_correction(
    user_client: AsyncClient,
) -> None:
    response = await user_client.post(
        "/api/vehicles",
        json={
            "name": "Volvo V60",
            "energy_type": "plugin_hybrid",
            "initial_odometer": 84_000,
            "odometer_offset": -120,
            "odometer_multiplier": "1.0125",
            "purchase_date": "2024-03-01",
            "purchase_price": "21500.00",
            "purchase_odometer": 84_000,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["energy_type"] == "plugin_hybrid"
    assert body["initial_odometer"] == 84_000
    assert body["odometer_offset"] == -120
    assert body["purchase_price"] == "21500.00"


async def test_an_unknown_energy_type_is_refused(user_client: AsyncClient) -> None:
    response = await user_client.post("/api/vehicles", json={"name": "X", "energy_type": "steam"})

    assert response.status_code == 422


async def test_a_zero_odometer_multiplier_is_refused(user_client: AsyncClient) -> None:
    """Zero would erase every distance the vehicle ever covered."""
    response = await user_client.post(
        "/api/vehicles", json={"name": "X", "odometer_multiplier": "0"}
    )

    assert response.status_code == 422


async def test_selling_a_vehicle_keeps_its_history(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client, purchase_price="20000.00")

    sold = await user_client.patch(
        f"/api/vehicles/{vehicle_id}",
        json={"status": "sold", "sale_date": "2026-09-01", "sale_price": "15750.00"},
    )

    assert sold.status_code == 200
    body = sold.json()
    assert body["status"] == "sold"
    assert body["sale_price"] == "15750.00"
    assert body["purchase_price"] == "20000.00"


async def test_the_garage_keeps_the_order_the_member_set(user_client: AsyncClient) -> None:
    first = await _vehicle(user_client, name="Volvo")
    second = await _vehicle(user_client, name="Corolla")
    third = await _vehicle(user_client, name="CB500F")

    reorder = await user_client.put(
        "/api/vehicles/order", json={"vehicle_ids": [third, first, second]}
    )

    assert reorder.status_code == 204
    listed = await user_client.get("/api/vehicles")
    assert [item["id"] for item in listed.json()] == [third, first, second]


async def test_reordering_refuses_a_vehicle_from_another_household(
    user_client: AsyncClient,
) -> None:
    response = await user_client.put(
        "/api/vehicles/order", json={"vehicle_ids": ["00000000-0000-0000-0000-000000000001"]}
    )

    assert response.status_code == 404


# --- work records ----------------------------------------------------------


async def test_a_work_record_carries_its_cost_breakdown_and_lines(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)

    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={
            "recorded_on": "2026-05-04",
            "kind": "maintenance",
            "description": "Revisão dos 120 mil",
            "total_cost": "246.00",
            "labour_cost": "90.00",
            "parts_cost": "140.00",
            "tax_cost": "36.00",
            "discount": "20.00",
            "items": [
                {"description": "Filtro de óleo", "quantity": "1", "unit_cost": "18.50"},
                {"description": "Óleo 5W30", "quantity": "5.5", "unit_cost": "12.00"},
            ],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["labour_cost"] == "90.00"
    assert [item["description"] for item in body["items"]] == ["Filtro de óleo", "Óleo 5W30"]
    assert Decimal(body["items"][1]["quantity"]) == Decimal("5.5")

    # And the lines survive the round trip through the database.
    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/work-records")
    assert [item["description"] for item in listed.json()[0]["items"]] == [
        "Filtro de óleo",
        "Óleo 5W30",
    ]


async def test_a_breakdown_that_does_not_add_up_is_refused(user_client: AsyncClient) -> None:
    """RF-INT-009: silently storing components that contradict the total would
    make every cost report wrong in a way nobody could see."""
    vehicle_id = await _vehicle(user_client)

    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={
            "recorded_on": "2026-05-04",
            "kind": "repair",
            "description": "Travões",
            "total_cost": "100.00",
            "labour_cost": "50.00",
            "parts_cost": "20.00",
        },
    )

    assert response.status_code == 422
    assert "70" in response.json()["detail"]


async def test_rounding_of_a_cent_is_tolerated(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)

    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={
            "recorded_on": "2026-05-04",
            "kind": "repair",
            "description": "Travões",
            "total_cost": "100.00",
            "labour_cost": "50.00",
            "parts_cost": "50.01",
        },
    )

    assert response.status_code == 201


async def test_a_total_on_its_own_is_still_accepted(user_client: AsyncClient) -> None:
    """Plenty of invoices only ever give one number."""
    vehicle_id = await _vehicle(user_client)

    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={
            "recorded_on": "2026-05-04",
            "kind": "repair",
            "description": "Travões",
            "total_cost": "100.00",
        },
    )

    assert response.status_code == 201


async def test_updating_the_lines_replaces_them(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={
            "recorded_on": "2026-05-04",
            "kind": "maintenance",
            "description": "Revisão",
            "items": [{"description": "Filtro", "quantity": "1"}],
        },
    )
    record_id = created.json()["id"]

    updated = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/work-records/{record_id}",
        json={"items": [{"description": "Pastilhas", "quantity": "4", "unit_cost": "15.00"}]},
    )

    assert updated.status_code == 200
    assert [item["description"] for item in updated.json()["items"]] == ["Pastilhas"]


async def test_leaving_items_out_of_an_update_keeps_them(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={
            "recorded_on": "2026-05-04",
            "kind": "maintenance",
            "description": "Revisão",
            "items": [{"description": "Filtro", "quantity": "1"}],
        },
    )
    record_id = created.json()["id"]

    updated = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/work-records/{record_id}",
        json={"description": "Revisão anual"},
    )

    assert [item["description"] for item in updated.json()["items"]] == ["Filtro"]


# --- expenses --------------------------------------------------------------


async def test_an_expense_carries_dates_reference_and_notes(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)

    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": "2026-01-10",
            "due_on": "2026-02-10",
            "paid_on": "2026-02-08",
            "category": "Seguro",
            "amount": "412.90",
            "reference": "AP-99213",
            "notes": "Renovação anual",
            "status": "paid",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["reference"] == "AP-99213"
    assert body["due_on"] == "2026-02-10"


async def test_a_pending_expense_past_its_due_date_reads_as_overdue(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": yesterday,
            "due_on": yesterday,
            "category": "IUC",
            "amount": "120.00",
            "status": "pending",
        },
    )

    assert created.json()["status"] == "overdue"


async def test_overdue_is_never_written_to_the_row(user_client: AsyncClient) -> None:
    """It is worked out on read; storing it would leave it stale by morning."""
    vehicle_id = await _vehicle(user_client)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": yesterday,
            "due_on": yesterday,
            "category": "IUC",
            "amount": "120.00",
            "status": "pending",
        },
    )
    record_id = created.json()["id"]

    # Paying it must work from the stored "pending", not from a persisted "overdue"
    # that the status field would reject as a value.
    paid = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/expenses/{record_id}",
        json={"status": "paid", "paid_on": date.today().isoformat()},
    )

    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"


async def test_recurrence_needs_both_an_interval_and_a_unit(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)

    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": "2026-01-10",
            "category": "IUC",
            "amount": "120.00",
            "recurrence_interval": 1,
        },
    )

    assert response.status_code == 422


async def test_the_next_occurrence_of_a_recurring_expense(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": "2026-01-10",
            "due_on": "2026-01-31",
            "category": "IUC",
            "amount": "120.00",
            "status": "paid",
            "recurrence_interval": 1,
            "recurrence_unit": "year",
        },
    )
    record_id = created.json()["id"]

    following = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses/{record_id}/next-occurrence"
    )

    assert following.status_code == 201, following.text
    body = following.json()
    assert body["due_on"] == "2027-01-31"
    assert body["amount"] == "120.00"
    assert body["status"] in {"pending", "overdue"}
    assert body["recurrence_parent_id"] == record_id


async def test_a_varying_amount_is_not_copied_forward(user_client: AsyncClient) -> None:
    """RF-DES-005: carrying last year's figure over would be a number nobody chose."""
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": "2026-01-10",
            "due_on": "2026-01-31",
            "category": "Eletricidade",
            "amount": "84.21",
            "recurrence_interval": 1,
            "recurrence_unit": "month",
            "recurrence_amount_varies": True,
        },
    )
    record_id = created.json()["id"]

    following = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses/{record_id}/next-occurrence"
    )

    assert following.json()["amount"] == "0.00"


async def test_the_next_occurrence_is_not_raised_twice(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": "2026-01-10",
            "category": "IUC",
            "amount": "120.00",
            "recurrence_interval": 1,
            "recurrence_unit": "year",
        },
    )
    record_id = created.json()["id"]
    await user_client.post(f"/api/vehicles/{vehicle_id}/expenses/{record_id}/next-occurrence")

    again = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses/{record_id}/next-occurrence"
    )

    assert again.status_code == 409


async def test_a_one_off_expense_has_no_next_occurrence(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={"issued_on": "2026-01-10", "category": "Lavagem", "amount": "12.00"},
    )
    record_id = created.json()["id"]

    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses/{record_id}/next-occurrence"
    )

    assert response.status_code == 409


# --- recurrence arithmetic -------------------------------------------------


def test_a_month_step_clamps_to_the_end_of_a_shorter_month() -> None:
    """A bill due on the 31st recurs on the 30th, not on the 1st of the month after."""
    assert next_occurrence_date(date(2026, 1, 31), 1, "month") == date(2026, 2, 28)
    assert next_occurrence_date(date(2026, 3, 31), 1, "month") == date(2026, 4, 30)


def test_a_year_step_handles_a_leap_day() -> None:
    assert next_occurrence_date(date(2024, 2, 29), 1, "year") == date(2025, 2, 28)


def test_day_and_year_steps() -> None:
    assert next_occurrence_date(date(2026, 1, 10), 30, "day") == date(2026, 2, 9)
    assert next_occurrence_date(date(2026, 1, 10), 2, "year") == date(2028, 1, 10)
