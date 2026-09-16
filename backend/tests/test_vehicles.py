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


async def test_update_status_and_soft_delete_vehicle(user_client: AsyncClient) -> None:
    created = (await user_client.post("/api/vehicles", json={"name": "Antigo"})).json()
    updated = await user_client.patch(
        f"/api/vehicles/{created['id']}",
        json={"name": "Atualizado", "status": "sold", "license_plate": "AA-00-AA"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Atualizado"
    assert updated.json()["status"] == "sold"
    removed = await user_client.delete(f"/api/vehicles/{created['id']}")
    assert removed.status_code == 204
    assert (await user_client.get(f"/api/vehicles/{created['id']}")).status_code == 404
    assert (await user_client.get("/api/vehicles")).json() == []


async def test_editor_cannot_manage_vehicle(register: RegisterFn) -> None:
    owner, _ = await register()
    vehicle = (await owner.post("/api/vehicles", json={"name": "Protegido"})).json()
    invite = (await owner.post("/api/household/invites", json={"role": "editor"})).json()
    editor, _ = await register(invite_token=invite["token"])
    assert (
        await editor.patch(f"/api/vehicles/{vehicle['id']}", json={"name": "Não"})
    ).status_code == 403
    assert (await editor.delete(f"/api/vehicles/{vehicle['id']}")).status_code == 403


async def test_vehicle_photos_require_household_membership(register: RegisterFn) -> None:
    owner, _ = await register()
    other, _ = await register()
    vehicle = (await owner.post("/api/vehicles", json={"name": "Private"})).json()
    response = await owner.post(
        f"/api/vehicles/{vehicle['id']}/photo",
        json={"content_type": "image/png", "content_base64": "iVBORw0KGgo="},
    )
    assert response.status_code == 200
    url = response.json()["photo_url"]
    assert (await owner.get(url)).status_code == 200
    assert (await other.get(url)).status_code == 404
    await owner.post("/auth/logout")
    assert (await owner.get(url)).status_code == 401
