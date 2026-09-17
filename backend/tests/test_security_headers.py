"""The hardening headers reach every response, including file downloads (RNF-SEG)."""

import base64

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.security_headers import API_CSP, DOCS_CSP, HSTS, install_security_headers
from app.main import app


def _probe_app(*, hsts: bool = False, allowed_hosts: list[str] | None = None) -> FastAPI:
    """A minimal app wearing the same middleware, for the cases the suite cannot
    reach through the real one: it is built once, at import, with test settings."""
    probe = FastAPI()
    install_security_headers(probe, hsts=hsts)
    if allowed_hosts is not None:
        probe.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    @probe.get("/probe")
    async def handler() -> dict[str, str]:
        return {"status": "ok"}

    return probe


async def test_api_responses_carry_the_strict_policy(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.headers["content-security-policy"] == API_CSP
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"


async def test_error_responses_are_hardened_too(client: AsyncClient) -> None:
    """A 401 is still a response a browser may be holding."""
    response = await client.get("/api/vehicles")

    assert response.status_code == 401
    assert response.headers["content-security-policy"] == API_CSP
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_downloads_are_not_sniffable(user_client: AsyncClient) -> None:
    """An uploaded file must not be re-typed by the browser into something executable."""
    created = await user_client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert created.status_code == 201
    vehicle_id = created.json()["id"]
    uploaded = await user_client.post(
        f"/api/vehicles/{vehicle_id}/attachments",
        json={
            "filename": "fatura.pdf",
            "content_type": "application/pdf",
            "content_base64": base64.b64encode(b"%PDF-1.4 fake receipt").decode(),
        },
    )
    assert uploaded.status_code == 201

    response = await user_client.get(
        f"/api/vehicles/{vehicle_id}/attachments/{uploaded.json()['id']}/download"
    )

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == API_CSP


async def test_docs_get_their_own_policy(client: AsyncClient) -> None:
    """Swagger UI loads from a CDN; the strict policy would leave a blank page."""
    response = await client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-security-policy"] == DOCS_CSP
    assert "https://cdn.jsdelivr.net" in response.headers["content-security-policy"]


async def test_hsts_is_absent_outside_production(client: AsyncClient) -> None:
    """The suite runs with ENVIRONMENT=test, where HSTS would pin localhost to HTTPS."""
    response = await client.get("/api/health")

    assert "strict-transport-security" not in response.headers


async def test_hsts_is_sent_when_enabled() -> None:
    transport = ASGITransport(app=_probe_app(hsts=True))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/probe")

    assert response.headers["strict-transport-security"] == HSTS


async def test_a_forged_host_is_refused() -> None:
    transport = ASGITransport(app=_probe_app(allowed_hosts=["rodiva.example"]))
    async with AsyncClient(transport=transport, base_url="http://rodiva.example") as ac:
        allowed = await ac.get("/probe")
    async with AsyncClient(transport=transport, base_url="http://attacker.example") as ac:
        refused = await ac.get("/probe")

    assert allowed.status_code == 200
    assert refused.status_code == 400


def test_the_host_allowlist_is_wired_into_the_app() -> None:
    """Guards against the middleware being dropped from main.py by a refactor."""
    assert TrustedHostMiddleware in {entry.cls for entry in app.user_middleware}
