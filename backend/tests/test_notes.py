from httpx import AsyncClient


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_and_list_notes(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    created = await user_client.post(
        f"/api/vehicles/{vehicle_id}/notes",
        json={"title": "Chave reserva", "content": "Fica na gaveta da cozinha."},
    )
    assert created.status_code == 201
    assert created.json()["pinned"] is False

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/notes")
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Chave reserva"


async def test_pinned_notes_are_listed_before_unpinned_ones(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/notes",
        json={"title": "Nota normal", "content": "Sem importância."},
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/notes",
        json={"title": "Nota fixada", "content": "Importante.", "pinned": True},
    )

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/notes")
    assert listed.status_code == 200
    assert [item["title"] for item in listed.json()] == ["Nota fixada", "Nota normal"]
