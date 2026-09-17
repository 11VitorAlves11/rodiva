"""OpenID Connect with PKCE (RF-AUT-006).

Driven against a provider built here — its own RSA key, its own JWKS — so the
signature check is exercised for real rather than stubbed past.
"""

import base64
import json
import time
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.services import oidc
from app.services.oidc import OidcError

ISSUER = "https://provider.example"
CLIENT_ID = "rodiva-test"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class Provider:
    """A minimal OpenID provider: one RSA key, a discovery document and a JWKS."""

    def __init__(self) -> None:
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        numbers = self.key.public_key().public_numbers()
        self.jwk = {
            "kty": "RSA",
            "kid": "test-key",
            "alg": "RS256",
            "n": _b64(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
            "e": _b64(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
        }

    @property
    def document(self) -> dict[str, Any]:
        return {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "jwks_uri": f"{ISSUER}/jwks",
        }

    def id_token(self, **overrides: Any) -> str:
        claims: dict[str, Any] = {
            "iss": ISSUER,
            "sub": "provider-subject-1",
            "aud": CLIENT_ID,
            "exp": int(time.time()) + 600,
            "iat": int(time.time()),
            "email": "Pessoa@Example.PT",
            "name": "Pessoa de Teste",
        }
        claims.update(overrides)
        header = _b64(json.dumps({"alg": "RS256", "kid": "test-key"}).encode())
        body = _b64(json.dumps(claims).encode())
        signing_input = f"{header}.{body}".encode()
        signature = self.key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        return f"{header}.{body}.{_b64(signature)}"

    def transport(self) -> httpx.MockTransport:
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("openid-configuration"):
                return httpx.Response(200, json=self.document)
            if request.url.path == "/jwks":
                return httpx.Response(200, json={"keys": [self.jwk]})
            return httpx.Response(404)

        return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Each test gets a fresh provider, so a cached key from the last one lies."""
    oidc._discovery_cache.clear()
    oidc._jwks_cache.clear()


def test_the_pkce_challenge_is_the_s256_of_the_verifier() -> None:
    """Without this the code interception PKCE exists to stop would still work."""
    from hashlib import sha256

    verifier, challenge = oidc.new_pkce_pair()

    assert challenge == _b64(sha256(verifier.encode("ascii")).digest())
    assert verifier != challenge


def test_the_authorization_url_carries_the_challenge_and_method() -> None:
    provider = Provider()

    url = oidc.authorization_url(
        provider.document,
        client_id=CLIENT_ID,
        redirect_uri="https://rodiva.example/auth/oidc/callback",
        scopes="openid email",
        state="a-state",
        challenge="a-challenge",
    )

    assert url.startswith(f"{ISSUER}/authorize?")
    assert "code_challenge=a-challenge" in url
    assert "code_challenge_method=S256" in url
    assert "response_type=code" in url


async def test_a_valid_id_token_yields_the_identity() -> None:
    provider = Provider()
    async with httpx.AsyncClient(transport=provider.transport()) as client:
        identity = await oidc.verify_id_token(
            provider.id_token(), provider.document, client_id=CLIENT_ID, client=client
        )

    assert identity.subject == "provider-subject-1"
    # Addresses are matched case-insensitively, so they are stored folded.
    assert identity.email == "pessoa@example.pt"
    assert identity.name == "Pessoa de Teste"


async def test_a_token_signed_by_someone_else_is_refused() -> None:
    """The whole point: claims alone would let anyone name themselves as anyone."""
    provider = Provider()
    impostor = Provider()
    async with httpx.AsyncClient(transport=provider.transport()) as client:
        with pytest.raises(OidcError, match="signature"):
            await oidc.verify_id_token(
                impostor.id_token(), provider.document, client_id=CLIENT_ID, client=client
            )


async def test_a_token_for_another_client_is_refused() -> None:
    provider = Provider()
    async with httpx.AsyncClient(transport=provider.transport()) as client:
        with pytest.raises(OidcError, match="another client"):
            await oidc.verify_id_token(
                provider.id_token(aud="someone-else"),
                provider.document,
                client_id=CLIENT_ID,
                client=client,
            )


async def test_an_expired_token_is_refused() -> None:
    provider = Provider()
    async with httpx.AsyncClient(transport=provider.transport()) as client:
        with pytest.raises(OidcError, match="expired"):
            await oidc.verify_id_token(
                provider.id_token(exp=int(time.time()) - 3600),
                provider.document,
                client_id=CLIENT_ID,
                client=client,
            )


async def test_a_token_from_another_issuer_is_refused() -> None:
    provider = Provider()
    async with httpx.AsyncClient(transport=provider.transport()) as client:
        with pytest.raises(OidcError, match="issued by someone else"):
            await oidc.verify_id_token(
                provider.id_token(iss="https://elsewhere.example"),
                provider.document,
                client_id=CLIENT_ID,
                client=client,
            )


async def test_a_mismatched_nonce_is_refused() -> None:
    """A replayed token from another sign-in carries the wrong nonce."""
    provider = Provider()
    async with httpx.AsyncClient(transport=provider.transport()) as client:
        with pytest.raises(OidcError, match="nonce"):
            await oidc.verify_id_token(
                provider.id_token(nonce="theirs"),
                provider.document,
                client_id=CLIENT_ID,
                nonce="ours",
                client=client,
            )


async def test_a_token_without_an_email_is_refused() -> None:
    """There would be no way to match the person to an account."""
    provider = Provider()
    async with httpx.AsyncClient(transport=provider.transport()) as client:
        with pytest.raises(OidcError, match="email"):
            await oidc.verify_id_token(
                provider.id_token(email=None),
                provider.document,
                client_id=CLIENT_ID,
                client=client,
            )


async def test_the_code_exchange_sends_the_verifier() -> None:
    """Omitting it would leave the flow as a plain authorization code grant."""
    provider = Provider()
    seen: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        from urllib.parse import parse_qs

        seen.update({k: v[0] for k, v in parse_qs(request.content.decode()).items()})
        return httpx.Response(200, json={"id_token": provider.id_token()})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await oidc.exchange_code(
            provider.document,
            code="the-code",
            verifier="the-verifier",
            client_id=CLIENT_ID,
            client_secret="",
            redirect_uri="https://rodiva.example/auth/oidc/callback",
            client=client,
        )

    assert seen["code_verifier"] == "the-verifier"
    assert seen["grant_type"] == "authorization_code"


async def test_a_token_response_without_an_id_token_is_refused() -> None:
    provider = Provider()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "only-this"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(OidcError, match="id_token"):
            await oidc.exchange_code(
                provider.document,
                code="x",
                verifier="y",
                client_id=CLIENT_ID,
                client_secret="",
                redirect_uri="https://rodiva.example/auth/oidc/callback",
                client=client,
            )


async def test_oidc_is_absent_from_the_options_when_unconfigured(client: httpx.AsyncClient) -> None:
    """The sign-in screen goes by this; offering a button that 404s would be worse."""
    response = await client.get("/auth/options")

    assert response.status_code == 200
    assert response.json()["oidc"] is False


async def test_starting_a_sign_in_is_refused_when_unconfigured(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/auth/oidc/start")

    assert response.status_code == 404
