from httpx import AsyncClient

from tests.conftest import RegisterFn


async def test_create_and_list_vehicle(user_client: AsyncClient) -> None:
    response = await user_client.post(
        "/api/vehicles",
        json={"name": "Golf da Ana", "make": "Volkswagen", "model": "Golf", "year": 2018},
    )
    assert response.status_code == 201
    vehicle = response.json()
    assert vehicle["name"] == "Golf da Ana"
    assert vehicle["status"] == "active"
    assert vehicle["distance_unit"] == "km"

    response = await user_client.get("/api/vehicles")
    assert response.status_code == 200
    vehicles = response.json()
    assert len(vehicles) == 1
    assert vehicles[0]["id"] == vehicle["id"]


async def test_vehicles_are_isolated_per_household(register: RegisterFn) -> None:
    client_a, _ = await register(household_name="Household A")
    client_b, _ = await register(household_name="Household B")

    await client_a.post("/api/vehicles", json={"name": "Only in A"})

    response = await client_b.get("/api/vehicles")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_vehicles_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/vehicles")
    assert response.status_code == 401
