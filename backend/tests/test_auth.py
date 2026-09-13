from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import TEST_PASSWORD, RegisterFn


async def test_register_creates_household_and_owner_membership(register: RegisterFn) -> None:
    _, body = await register(household_name="Alves household")
    assert body["membership"]["household_name"] == "Alves household"
    assert body["membership"]["role"] == "owner"


async def test_register_rejects_duplicate_email(register: RegisterFn) -> None:
    _, body = await register()
    ac = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        response = await ac.post(
            "/auth/register",
            json={
                "email": body["user"]["email"],
                "password": TEST_PASSWORD,
                "household_name": "Another household",
            },
        )
        assert response.status_code == 409
    finally:
        await ac.aclose()


async def test_login_returns_session_cookie(register: RegisterFn) -> None:
    _, body = await register()
    email = body["user"]["email"]
    ac = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        response = await ac.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
        assert response.status_code == 200
        assert "rodiva_session" in response.cookies
    finally:
        await ac.aclose()


async def test_login_rejects_wrong_password(register: RegisterFn) -> None:
    _, body = await register()
    email = body["user"]["email"]
    ac = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    try:
        response = await ac.post("/auth/login", json={"email": email, "password": "wrong-password"})
        assert response.status_code == 401
    finally:
        await ac.aclose()


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_returns_current_user(user_client: AsyncClient) -> None:
    response = await user_client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["membership"]["role"] == "owner"


async def test_logout_clears_session(user_client: AsyncClient) -> None:
    response = await user_client.post("/auth/logout")
    assert response.status_code == 204
    response = await user_client.get("/auth/me")
    assert response.status_code == 401
