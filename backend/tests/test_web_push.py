"""Web Push: VAPID tokens and aes128gcm payloads (RF-NOT-002, RF-PWA-012).

The encryption is checked by decrypting what it produces, following RFC 8291 in
the other direction. A payload that only round-trips through its own encoder
would prove nothing; this proves a browser holding the private half can read it.
"""

import json
import struct

import httpx
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from httpx import AsyncClient

from app.services import web_push
from app.services.web_push import b64, unb64


def _browser_keys() -> tuple[ec.EllipticCurvePrivateKey, str, str]:
    """A subscription's key pair and auth secret, as a browser would make them."""
    private = ec.generate_private_key(ec.SECP256R1())
    p256dh = b64(
        private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
    )
    auth = b64(b"0123456789abcdef")
    return private, p256dh, auth


def _decrypt(body: bytes, private: ec.EllipticCurvePrivateKey, p256dh: str, auth: str) -> bytes:
    salt = body[:16]
    (_record_size,) = struct.unpack("!I", body[16:20])
    key_length = body[20]
    server_public_raw = body[21 : 21 + key_length]
    sealed = body[21 + key_length :]

    server_public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), server_public_raw)
    shared = private.exchange(ec.ECDH(), server_public)
    prk = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=unb64(auth),
        info=b"WebPush: info\x00" + unb64(p256dh) + server_public_raw,
    ).derive(shared)
    content_key = HKDF(
        algorithm=hashes.SHA256(), length=16, salt=salt, info=b"Content-Encoding: aes128gcm\x00"
    ).derive(prk)
    nonce = HKDF(
        algorithm=hashes.SHA256(), length=12, salt=salt, info=b"Content-Encoding: nonce\x00"
    ).derive(prk)
    plain = AESGCM(content_key).decrypt(nonce, sealed, None)
    return plain.rstrip(b"\x02")


def test_a_payload_can_be_decrypted_by_the_subscription_it_was_sealed_to() -> None:
    private, p256dh, auth = _browser_keys()

    body = web_push.encrypt_payload(b'{"title":"Revisao"}', p256dh, auth)

    assert _decrypt(body, private, p256dh, auth) == b'{"title":"Revisao"}'


def test_another_subscription_cannot_read_it() -> None:
    """The payload is bound to the subscription's own key, not merely obscured."""
    _, p256dh, auth = _browser_keys()
    eavesdropper, _, _ = _browser_keys()

    body = web_push.encrypt_payload(b"segredo", p256dh, auth)

    with pytest.raises(InvalidTag):
        _decrypt(body, eavesdropper, p256dh, auth)


def test_each_message_uses_a_fresh_salt_and_key() -> None:
    """Reusing them would leak that two notifications carried the same text."""
    _, p256dh, auth = _browser_keys()

    first = web_push.encrypt_payload(b"mesmo texto", p256dh, auth)
    second = web_push.encrypt_payload(b"mesmo texto", p256dh, auth)

    assert first != second
    assert first[:16] != second[:16]


def test_the_vapid_header_names_the_push_service_it_is_for() -> None:
    """A token for one service must not be replayable against another (RFC 8292)."""
    public_key, private_key = web_push.generate_vapid_keys()

    header = web_push.build_vapid_header(
        "https://fcm.googleapis.com/fcm/send/abc", public_key, private_key, "mailto:a@b.pt"
    )

    assert header.startswith("vapid t=")
    assert f"k={public_key}" in header
    token = header[len("vapid t=") :].split(",")[0]
    claims = json.loads(unb64(token.split(".")[1]))
    assert claims["aud"] == "https://fcm.googleapis.com"
    assert claims["sub"] == "mailto:a@b.pt"


def test_the_vapid_signature_verifies_against_the_public_key() -> None:
    public_key, private_key = web_push.generate_vapid_keys()
    header = web_push.build_vapid_header(
        "https://push.example/x", public_key, private_key, "mailto:a@b.pt"
    )
    token = header[len("vapid t=") :].split(",")[0]
    signed, signature = token.rsplit(".", 1)

    from cryptography.hazmat.primitives.asymmetric import utils as asym_utils

    raw = unb64(signature)
    der = asym_utils.encode_dss_signature(
        int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")
    )
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64(public_key))

    # Raises if the signature does not match; that is the assertion.
    public.verify(der, signed.encode(), ec.ECDSA(hashes.SHA256()))


async def test_a_gone_endpoint_is_reported_as_expired() -> None:
    """410 means the browser is gone for good, so the row should be dropped."""
    _, p256dh, auth = _browser_keys()
    public_key, private_key = web_push.generate_vapid_keys()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(410)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await web_push.send(
            endpoint="https://push.example/gone",
            p256dh=p256dh,
            auth=auth,
            payload={"title": "x"},
            public_key=public_key,
            private_key=private_key,
            subject="mailto:a@b.pt",
            client=client,
        )

    assert result.expired is True


async def test_the_request_carries_the_headers_a_push_service_requires() -> None:
    _, p256dh, auth = _browser_keys()
    public_key, private_key = web_push.generate_vapid_keys()
    seen: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(201)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await web_push.send(
            endpoint="https://push.example/ok",
            p256dh=p256dh,
            auth=auth,
            payload={"title": "x"},
            public_key=public_key,
            private_key=private_key,
            subject="mailto:a@b.pt",
            client=client,
        )

    assert result.expired is False
    assert seen["content-encoding"] == "aes128gcm"
    assert seen["authorization"].startswith("vapid t=")
    assert seen["ttl"] == str(web_push.DEFAULT_TTL_SECONDS)


async def test_the_key_endpoint_says_push_is_off_when_unconfigured(
    user_client: AsyncClient,
) -> None:
    """The UI needs this: asking for permission it cannot act on burns the prompt."""
    response = await user_client.get("/api/push/key")

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "public_key": ""}


async def test_subscribing_is_refused_without_keys(user_client: AsyncClient) -> None:
    response = await user_client.post(
        "/api/push",
        json={"endpoint": "https://push.example/abc", "p256dh": "x" * 40, "auth": "y" * 20},
    )

    assert response.status_code == 409
