"""Symmetric encryption for OAuth tokens at rest (RF-GCAL-007).

There is no encryption-at-rest primitive elsewhere in the codebase — `itsdangerous`
is used only to *sign* the session cookie, not to hide data — so this is new.
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    # Derived from SECRET_KEY (sha256 -> 32 bytes -> urlsafe base64) rather than a
    # second dedicated env var: one fewer secret to provision and rotate, at the
    # cost of tokens becoming unreadable if SECRET_KEY ever rotates — acceptable
    # since rotating it already invalidates every session.
    key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().secret_key.encode()).digest())
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as error:
        raise ValueError("Could not decrypt stored token") from error
