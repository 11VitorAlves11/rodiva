from httpx import AsyncClient


async def test_health_is_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_root_reports_name_and_version(client: AsyncClient) -> None:
    response = await client.get("/api")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Rodiva"
    assert body["version"] == "0.2.0"
