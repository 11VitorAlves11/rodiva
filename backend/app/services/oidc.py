"""OpenID Connect with PKCE (RF-AUT-006).

Only the authorization code flow, and always with PKCE: this is a public client
served from a browser, so a code intercepted on the redirect is worthless
without the verifier that never left the server.

The ID token's signature is verified against the provider's published JWKS. A
token accepted on its claims alone would let anyone who can reach the callback
name themselves as any user.
"""

import base64
import json
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils

#: A provider's configuration rarely changes, and refetching it on every sign-in
#: would make the provider's availability part of every request's latency.
_DISCOVERY_TTL_SECONDS = 60 * 60
_discovery_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}

#: Tolerance for a provider's clock running slightly ahead of ours.
CLOCK_SKEW_SECONDS = 60


class OidcError(Exception):
    """Anything that means this sign-in cannot be trusted."""


@dataclass(frozen=True)
class Identity:
    subject: str
    email: str
    name: str | None


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def new_pkce_pair() -> tuple[str, str]:
    """A verifier and its S256 challenge (RFC 7636)."""
    verifier = _b64(secrets.token_bytes(64))
    challenge = _b64(sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


async def discover(issuer: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    cached = _discovery_cache.get(issuer)
    if cached and cached[0] > time.time():
        return cached[1]
    url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    document = await _get_json(url, client)
    for required in ("authorization_endpoint", "token_endpoint", "jwks_uri", "issuer"):
        if required not in document:
            raise OidcError(f"The provider's configuration has no {required}")
    _discovery_cache[issuer] = (time.time() + _DISCOVERY_TTL_SECONDS, document)
    return document


async def _get_json(url: str, client: httpx.AsyncClient | None) -> dict[str, Any]:
    owned = client is None
    http = client or httpx.AsyncClient(timeout=10)
    try:
        response = await http.get(url)
    finally:
        if owned:
            await http.aclose()
    if response.status_code >= 400:
        raise OidcError(f"The provider answered {response.status_code} for {url}")
    return dict(response.json())


async def _jwks(uri: str, client: httpx.AsyncClient | None) -> dict[str, Any]:
    cached = _jwks_cache.get(uri)
    if cached and cached[0] > time.time():
        return cached[1]
    document = await _get_json(uri, client)
    _jwks_cache[uri] = (time.time() + _DISCOVERY_TTL_SECONDS, document)
    return document


def authorization_url(
    document: dict[str, Any],
    *,
    client_id: str,
    redirect_uri: str,
    scopes: str,
    state: str,
    challenge: str,
) -> str:
    from urllib.parse import urlencode

    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{document['authorization_endpoint']}?{query}"


async def exchange_code(
    document: dict[str, Any],
    *,
    code: str,
    verifier: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": verifier,
    }
    if client_secret:
        form["client_secret"] = client_secret
    owned = client is None
    http = client or httpx.AsyncClient(timeout=10)
    try:
        response = await http.post(document["token_endpoint"], data=form)
    finally:
        if owned:
            await http.aclose()
    if response.status_code >= 400:
        raise OidcError("The provider refused the authorization code")
    body = dict(response.json())
    if "id_token" not in body:
        raise OidcError("The provider returned no id_token")
    return body


def _public_key(jwk: dict[str, Any]) -> Any:
    if jwk.get("kty") == "RSA":
        return rsa.RSAPublicNumbers(
            e=int.from_bytes(_unb64(jwk["e"]), "big"), n=int.from_bytes(_unb64(jwk["n"]), "big")
        ).public_key()
    if jwk.get("kty") == "EC":
        curves = {"P-256": ec.SECP256R1(), "P-384": ec.SECP384R1(), "P-521": ec.SECP521R1()}
        curve = curves.get(jwk.get("crv", ""))
        if curve is None:
            raise OidcError(f"Unsupported curve: {jwk.get('crv')}")
        return ec.EllipticCurvePublicNumbers(
            x=int.from_bytes(_unb64(jwk["x"]), "big"),
            y=int.from_bytes(_unb64(jwk["y"]), "big"),
            curve=curve,
        ).public_key()
    raise OidcError(f"Unsupported key type: {jwk.get('kty')}")


def _verify_signature(token: str, jwk: dict[str, Any], algorithm: str) -> None:
    signed, signature = token.rsplit(".", 1)
    key = _public_key(jwk)
    raw = _unb64(signature)
    if algorithm.startswith("RS"):
        key.verify(raw, signed.encode(), padding.PKCS1v15(), hashes.SHA256())
    elif algorithm.startswith("ES"):
        half = len(raw) // 2
        der = utils.encode_dss_signature(
            int.from_bytes(raw[:half], "big"), int.from_bytes(raw[half:], "big")
        )
        key.verify(der, signed.encode(), ec.ECDSA(hashes.SHA256()))
    else:
        raise OidcError(f"Unsupported signing algorithm: {algorithm}")


async def verify_id_token(
    id_token: str,
    document: dict[str, Any],
    *,
    client_id: str,
    nonce: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> Identity:
    """Check the token's signature and claims, and return who it says this is."""
    try:
        header_raw, payload_raw, _ = id_token.split(".")
        header = json.loads(_unb64(header_raw))
        claims = json.loads(_unb64(payload_raw))
    except (ValueError, json.JSONDecodeError) as error:
        raise OidcError("The id_token is malformed") from error

    keys = (await _jwks(document["jwks_uri"], client)).get("keys", [])
    kid = header.get("kid")
    matching = [key for key in keys if kid is None or key.get("kid") == kid]
    if not matching:
        raise OidcError("No published key matches the id_token")
    last_error: Exception | None = None
    for key in matching:
        try:
            _verify_signature(id_token, key, header.get("alg", "RS256"))
            break
        except Exception as error:  # noqa: BLE001 - try the next published key
            last_error = error
    else:
        raise OidcError("The id_token signature does not verify") from last_error

    now = time.time()
    if claims.get("iss") != document["issuer"]:
        raise OidcError("The id_token was issued by someone else")
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if client_id not in audiences:
        raise OidcError("The id_token was issued for another client")
    if float(claims.get("exp", 0)) + CLOCK_SKEW_SECONDS < now:
        raise OidcError("The id_token has expired")
    if float(claims.get("iat", now)) - CLOCK_SKEW_SECONDS > now:
        raise OidcError("The id_token is stamped in the future")
    if nonce is not None and claims.get("nonce") != nonce:
        raise OidcError("The id_token does not carry the nonce we sent")

    subject = claims.get("sub")
    email = claims.get("email")
    if not subject:
        raise OidcError("The id_token carries no subject")
    if not email:
        raise OidcError("The provider returned no email address")
    return Identity(subject=str(subject), email=str(email).lower(), name=claims.get("name"))
