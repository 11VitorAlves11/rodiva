from httpx import AsyncClient

from tests.conftest import RegisterFn


async def test_charging_efficiency_and_costs(user_client: AsyncClient) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Electric"})).json()
    path = f"/api/vehicles/{vehicle['id']}/charging-records"
    base = {
        "recorded_on": "2026-01-01",
        "odometer_reading": 1000,
        "energy_kwh": "40",
        "total_cost": "0",
        "soc_start": 20,
        "soc_end": 80,
    }
    first = await user_client.post(path, json=base)
    assert first.status_code == 201, first.text
    assert first.json()["unit_price"] == "0.000"
    assert first.json()["efficiency_kwh_per_100km"] is None
    second = await user_client.post(
        path,
        json={
            **base,
            "recorded_on": "2026-01-02",
            "odometer_reading": 1100,
            "energy_kwh": "10",
            "total_cost": "3",
            "soc_end": 60,
        },
    )
    assert second.status_code == 201
    assert second.json()["efficiency_kwh_per_100km"] is None
    third = await user_client.post(
        path,
        json={
            **base,
            "recorded_on": "2026-01-03",
            "odometer_reading": 1200,
            "energy_kwh": "20",
            "total_cost": "5",
        },
    )
    assert third.status_code == 201
    assert third.json()["efficiency_kwh_per_100km"] == "15.000"
    report = (await user_client.get("/api/reports/summary")).json()
    assert report["total_cost"] == "8.00"
    assert report["vehicles"][0]["monthly"][0]["charging"] == "8.00"
    assert "charging" in (await user_client.get("/api/reports/export.csv")).text
    changed = await user_client.patch(
        f"{path}/{second.json()['id']}",
        json={
            **base,
            "recorded_on": "2026-01-02",
            "odometer_reading": 1100,
            "energy_kwh": "20",
            "total_cost": "3",
            "soc_end": 60,
        },
    )
    assert changed.status_code == 200
    latest = (await user_client.get(path)).json()[0]
    assert latest["efficiency_kwh_per_100km"] == "20.000"
    assert (await user_client.delete(f"{path}/{second.json()['id']}")).status_code == 204
    assert (await user_client.get(path)).json()[0]["efficiency_kwh_per_100km"] == "10.000"


async def test_charging_miles_are_converted(user_client: AsyncClient) -> None:
    vehicle = (
        await user_client.post("/api/vehicles", json={"name": "Miles", "distance_unit": "mi"})
    ).json()
    path = f"/api/vehicles/{vehicle['id']}/charging-records"
    base = {
        "recorded_on": "2026-01-01",
        "odometer_reading": 100,
        "energy_kwh": "20",
        "total_cost": "5",
        "soc_end": 80,
    }
    assert (await user_client.post(path, json=base)).status_code == 201
    row = await user_client.post(
        path, json={**base, "recorded_on": "2026-01-02", "odometer_reading": 200}
    )
    assert row.json()["efficiency_kwh_per_100km"] == "12.427"


async def test_charging_validation_and_tenant_access(register: RegisterFn) -> None:
    owner, _ = await register()
    other, _ = await register()
    vehicle = (await owner.post("/api/vehicles", json={"name": "Electric"})).json()
    path = f"/api/vehicles/{vehicle['id']}/charging-records"
    base = {"recorded_on": "2026-01-01", "energy_kwh": "20", "total_cost": "5"}
    assert (await other.get(path)).status_code == 404
    for changes in [
        {"energy_kwh": "0"},
        {"total_cost": "-1"},
        {"soc_start": 90, "soc_end": 80},
        {"soc_end": 101},
    ]:
        assert (await owner.post(path, json={**base, **changes})).status_code == 422
    await owner.post(path, json={**base, "odometer_reading": 1000})
    assert (
        await owner.post(path, json={**base, "recorded_on": "2026-01-02", "odometer_reading": 900})
    ).status_code == 422
    assert len((await owner.get(path)).json()) == 1
    invite = (await owner.post("/api/household/invites", json={"role": "reader"})).json()
    await other.post(f"/auth/invites/{invite['token']}/accept")
    assert (await other.get(path)).status_code == 200
    assert (await other.post(path, json=base)).status_code == 403
