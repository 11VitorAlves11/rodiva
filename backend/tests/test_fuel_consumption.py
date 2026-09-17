"""The consumption calculation, which is the product's central figure.

Full-tank accounting: a full fill measures everything burnt since the last full
one, so partial fills in between count towards that window rather than producing
a figure of their own.
"""

from httpx import AsyncClient


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert response.status_code == 201
    return response.json()["id"]


async def _fill(
    client: AsyncClient,
    vehicle_id: str,
    *,
    on: str,
    odometer: int,
    litres: str,
    full: bool = True,
    excluded: bool = False,
    price: str = "100.00",
) -> dict:
    response = await client.post(
        f"/api/vehicles/{vehicle_id}/fuel-records",
        json={
            "recorded_on": on,
            "odometer_reading": odometer,
            "volume_litres": litres,
            "total_price": price,
            "full_tank": full,
            "excluded_from_consumption": excluded,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _consumptions(client: AsyncClient, vehicle_id: str) -> list[str | None]:
    listed = await client.get(f"/api/vehicles/{vehicle_id}/fuel-records")
    assert listed.status_code == 200
    rows = sorted(listed.json(), key=lambda row: (row["recorded_on"], row["id"]))
    return [row["consumption_l_per_100km"] for row in rows]


async def test_partial_fills_count_towards_the_next_full_tank(user_client: AsyncClient) -> None:
    """The partial fill has no window of its own; its litres belong to the next full one."""
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    await _fill(
        user_client, vehicle_id, on="2026-01-10", odometer=10_300, litres="20.000", full=False
    )
    await _fill(user_client, vehicle_id, on="2026-01-20", odometer=10_800, litres="30.000")

    # 50 litres over 800 km, the partial and the full both counted: 6.250 l/100 km.
    assert await _consumptions(user_client, vehicle_id) == [None, None, "6.250"]


async def test_an_excluded_fill_leaves_the_window_but_not_the_distance(
    user_client: AsyncClient,
) -> None:
    """Fuel put in a jerrycan was not burnt by the car, so its litres do not count."""
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    await _fill(
        user_client,
        vehicle_id,
        on="2026-01-10",
        odometer=10_300,
        litres="20.000",
        full=False,
        excluded=True,
    )
    await _fill(user_client, vehicle_id, on="2026-01-20", odometer=10_800, litres="40.000")

    # Only the final 40 litres count across the 800 km.
    assert await _consumptions(user_client, vehicle_id) == [None, None, "5.000"]


async def test_a_fill_added_out_of_order_lands_in_its_place(user_client: AsyncClient) -> None:
    """A receipt found later must not be treated as the most recent fill."""
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    await _fill(user_client, vehicle_id, on="2026-03-01", odometer=11_000, litres="60.000")

    await _fill(user_client, vehicle_id, on="2026-02-01", odometer=10_500, litres="25.000")

    # January→February: 25 l over 500 km. February→March: 60 l over 500 km.
    assert await _consumptions(user_client, vehicle_id) == [None, "5.000", "12.000"]


async def test_no_distance_between_two_fills_yields_no_figure(user_client: AsyncClient) -> None:
    """Topping up twice at the same odometer would divide by zero."""
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    await _fill(user_client, vehicle_id, on="2026-01-02", odometer=10_000, litres="5.000")

    assert await _consumptions(user_client, vehicle_id) == [None, None]


async def test_deleting_a_middle_fill_widens_the_window(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    middle = await _fill(user_client, vehicle_id, on="2026-02-01", odometer=10_500, litres="30.000")
    await _fill(user_client, vehicle_id, on="2026-03-01", odometer=11_000, litres="40.000")
    assert await _consumptions(user_client, vehicle_id) == [None, "6.000", "8.000"]

    removed = await user_client.delete(f"/api/vehicles/{vehicle_id}/fuel-records/{middle['id']}")
    assert removed.status_code == 204

    # The window is now the full 1000 km, covered by the last fill's 40 litres.
    assert await _consumptions(user_client, vehicle_id) == [None, "4.000"]


async def test_restoring_a_fill_from_the_bin_puts_its_figure_back(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    middle = await _fill(user_client, vehicle_id, on="2026-02-01", odometer=10_500, litres="30.000")
    await _fill(user_client, vehicle_id, on="2026-03-01", odometer=11_000, litres="40.000")
    await user_client.delete(f"/api/vehicles/{vehicle_id}/fuel-records/{middle['id']}")

    restored = await user_client.post(f"/api/trash/fuel_record/{middle['id']}/restore")

    assert restored.status_code == 204
    assert await _consumptions(user_client, vehicle_id) == [None, "6.000", "8.000"]


async def test_a_fill_without_an_odometer_reading_produces_no_figure(
    user_client: AsyncClient,
) -> None:
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/fuel-records",
        json={
            "recorded_on": "2026-02-01",
            "volume_litres": "30.000",
            "total_price": "50.00",
            "full_tank": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["consumption_l_per_100km"] is None


async def test_the_figure_is_rounded_half_up_to_three_places(user_client: AsyncClient) -> None:
    """A fixed rounding rule, so the same data never reads two ways."""
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    second = await _fill(user_client, vehicle_id, on="2026-02-01", odometer=10_700, litres="42.700")

    # 42.7 * 100 / 700 = 6.1000 exactly; a third place that is not noise.
    assert second["consumption_l_per_100km"] == "6.100"


async def test_a_run_of_partial_fills_accumulates(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await _fill(user_client, vehicle_id, on="2026-01-01", odometer=10_000, litres="50.000")
    for day, odometer in ((5, 10_200), (10, 10_400), (15, 10_600)):
        await _fill(
            user_client,
            vehicle_id,
            on=f"2026-01-{day:02d}",
            odometer=odometer,
            litres="15.000",
            full=False,
        )
    await _fill(user_client, vehicle_id, on="2026-01-20", odometer=11_000, litres="20.000")

    # 45 litres of partials plus 20 at the end, across 1000 km.
    assert (await _consumptions(user_client, vehicle_id))[-1] == "6.500"
