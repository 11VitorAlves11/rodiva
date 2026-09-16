import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.main import app
from app.models import PasswordReset
from tests.conftest import TEST_PASSWORD, RegisterFn


async def test_recovery_is_single_use_and_revokes_sessions(
    register: RegisterFn, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, body = await register()
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "mail.example.com")
    monkeypatch.setattr(settings, "smtp_from", "rodiva@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.routes.auth.send_password_reset") as send:
            response = await client.post(
                "/auth/forgot-password", json={"email": body["user"]["email"]}
            )
            assert response.status_code == 202
            token = send.call_args.args[2]
            unknown = await client.post(
                "/auth/forgot-password", json={"email": "unknown@example.com"}
            )
            assert unknown.json() == response.json()
            assert send.call_count == 1
        async with get_sessionmaker()() as db:
            stored = await db.scalar(
                select(PasswordReset).where(
                    PasswordReset.token_hash == hashlib.sha256(token.encode()).hexdigest()
                )
            )
            assert stored is not None
            assert stored.token_hash != token
        response = await client.post(
            "/auth/reset-password", json={"token": token, "password": "brand-new-password"}
        )
        assert response.status_code == 204
        assert (await owner.get("/auth/me")).status_code == 401
        assert (
            await client.post(
                "/auth/reset-password", json={"token": token, "password": "another-password"}
            )
        ).status_code == 400
        assert (
            await client.post(
                "/auth/login", json={"email": body["user"]["email"], "password": TEST_PASSWORD}
            )
        ).status_code == 401
        assert (
            await client.post(
                "/auth/login",
                json={"email": body["user"]["email"], "password": "brand-new-password"},
            )
        ).status_code == 200


async def test_expired_reset_is_rejected(
    register: RegisterFn, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner, body = await register()
    monkeypatch.setattr(get_settings(), "smtp_host", "mail.example.com")
    monkeypatch.setattr(get_settings(), "smtp_from", "rodiva@example.com")
    with patch("app.api.routes.auth.send_password_reset") as send:
        await owner.post("/auth/forgot-password", json={"email": body["user"]["email"]})
        token = send.call_args.args[2]
    async with get_sessionmaker()() as db:
        stored = await db.get(PasswordReset, hashlib.sha256(token.encode()).hexdigest())
        assert stored is not None
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await db.commit()
    assert (
        await owner.post(
            "/auth/reset-password", json={"token": token, "password": "new-password-value"}
        )
    ).status_code == 400
    assert (await owner.get("/auth/me")).status_code == 200


async def test_login_throttle_survives_requests(register: RegisterFn) -> None:
    owner, body = await register()
    for _ in range(10):
        response = await owner.post(
            "/auth/login", json={"email": body["user"]["email"], "password": "wrong"}
        )
        assert response.status_code == 401
    response = await owner.post(
        "/auth/login", json={"email": body["user"]["email"], "password": TEST_PASSWORD}
    )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "900"
