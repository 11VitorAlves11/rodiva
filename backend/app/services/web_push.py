"""Web Push: VAPID authentication and aes128gcm payloads (RF-NOT-002, RF-PWA-012).

Implemented against RFC 8292 (VAPID) and RFC 8291/8188 (the payload encryption)
using `cryptography`, which the project already depends on, rather than pulling
in a push library for what amounts to one ECDH, one HKDF and one AES-GCM seal.
"""

import base64
import json
import os
import struct
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

#: How long a push service may sit on an undelivered message.
DEFAULT_TTL_SECONDS = 60 * 60 * 24

#: RFC 8292: a VAPID token is short-lived so a captured one is soon useless.
TOKEN_LIFETIME_SECONDS = 60 * 60 * 12


def b64(raw: bytes) -> str:
    """base64url with the padding stripped, which is what every push API uses."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


@dataclass(frozen=True)
class PushResult:
    status_code: int
    #: True when the subscription is gone for good and should be forgotten.
    expired: bool


def generate_vapid_keys() -> tuple[str, str]:
    """A fresh VAPID pair, as the base64url strings the settings take."""
    private = ec.generate_private_key(ec.SECP256R1())
    public = private.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    value = private.private_numbers().private_value
    return b64(public), b64(value.to_bytes(32, "big"))


def _load_private_key(encoded: str) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(int.from_bytes(unb64(encoded), "big"), ec.SECP256R1())


def build_vapid_header(endpoint: str, public_key: str, private_key: str, subject: str) -> str:
    """The Authorization header a push service checks before accepting a message."""
    origin = urlparse(endpoint)
    claims = {
        "aud": f"{origin.scheme}://{origin.netloc}",
        "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS,
        "sub": subject,
    }
    header = b64(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    body = b64(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()

    signature = _load_private_key(private_key).sign(signing_input, ec.ECDSA(hashes.SHA256()))
    # JOSE wants the raw r||s pair, not the DER structure `sign` returns.
    r, s = utils.decode_dss_signature(signature)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"vapid t={header}.{body}.{b64(raw)}, k={public_key}"


def encrypt_payload(payload: bytes, p256dh: str, auth: str) -> bytes:
    """Seal `payload` for one subscription, as a Content-Encoding: aes128gcm body."""
    client_public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64(p256dh))
    server_private = ec.generate_private_key(ec.SECP256R1())
    server_public = server_private.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    shared = server_private.exchange(ec.ECDH(), client_public)
    salt = os.urandom(16)
    auth_secret = unb64(auth)

    # RFC 8291 §3.4: the shared secret is first bound to both public keys, so a
    # key reused against another subscription derives nothing useful.
    prk = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=auth_secret,
        info=b"WebPush: info\x00" + unb64(p256dh) + server_public,
    ).derive(shared)
    content_key = HKDF(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        info=b"Content-Encoding: aes128gcm\x00",
    ).derive(prk)
    nonce = HKDF(
        algorithm=hashes.SHA256(),
        length=12,
        salt=salt,
        info=b"Content-Encoding: nonce\x00",
    ).derive(prk)

    # RFC 8188: a single record, so the padding delimiter is 0x02.
    sealed = AESGCM(content_key).encrypt(nonce, payload + b"\x02", None)
    record_size = len(sealed) + 16 + 1 + len(server_public)
    header = salt + struct.pack("!IB", record_size, len(server_public)) + server_public
    return header + sealed


async def send(
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    payload: dict[str, Any],
    public_key: str,
    private_key: str,
    subject: str,
    ttl: int = DEFAULT_TTL_SECONDS,
    client: httpx.AsyncClient | None = None,
) -> PushResult:
    """Deliver one notification, saying whether the subscription has expired."""
    body = encrypt_payload(json.dumps(payload).encode(), p256dh, auth)
    headers = {
        "Authorization": build_vapid_header(endpoint, public_key, private_key, subject),
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        "TTL": str(ttl),
    }
    owned = client is None
    http = client or httpx.AsyncClient(timeout=10)
    try:
        response = await http.post(endpoint, content=body, headers=headers)
    finally:
        if owned:
            await http.aclose()
    # 404 and 410 are the push service saying this endpoint will never work
    # again; anything else may be worth another go later.
    return PushResult(status_code=response.status_code, expired=response.status_code in {404, 410})
