from httpx import AsyncClient


async def test_v1_matches_existing_api(user_client: AsyncClient) -> None:
    created = await user_client.post("/api/v1/vehicles", json={"name": "Versioned"})
    assert created.status_code == 201
    response = await user_client.get("/api/vehicles")
    assert response.json()[0]["id"] == created.json()["id"]
    assert (await user_client.get("/api/v1/vehicles")).json() == response.json()


async def test_validation_errors_have_correlation_and_do_not_echo_secrets(
    client: AsyncClient,
) -> None:
    secret = "short"
    response = await client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": secret, "household_name": "Test"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "validation_error"
    assert data["fields"][0]["field"] == "body.password"
    assert data["correlation_id"] == response.headers["X-Request-ID"]
    assert secret not in response.text
    denied = await client.get("/api/v1/vehicles")
    assert denied.json()["code"] == "http_401"
