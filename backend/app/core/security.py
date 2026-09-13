"""Password hashing and the signed session cookie.

The session is stateless: a signed token carrying the user id and an issue time,
verified on every request. No session table, no session store — one fewer service
to run at home, at the cost of not being able to revoke a single session early
(RF-AUT-003/RF-AUT-007 will need a revocation list when that matters).
"""

import uuid
from datetime import UTC, datetime

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings

# bcrypt silently ignores everything past 72 bytes, so an over-long password would
# otherwise be a shorter password in disguise.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 10

#: How far into the future a session token may be stamped and still be read.
#: Wide enough for a clock that stepped back, far too narrow to extend a session.
MAX_CLOCK_SKEW_SECONDS = 60

SESSION_SALT = "rodiva.session"


class PasswordTooLongError(ValueError):
    """Raised when a password exceeds what bcrypt can actually hash."""


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(f"password exceeds {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        return False


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=SESSION_SALT)


def issue_session(user_id: uuid.UUID) -> str:
    return _serializer().dumps(str(user_id))


def read_session(token: str) -> uuid.UUID | None:
    """Return the user id carried by a valid, unexpired token, else None."""
    serializer = _serializer()
    max_age = get_settings().session_max_age
    try:
        raw = serializer.loads(token, max_age=max_age)
    except SignatureExpired as expired:
        if not _within_clock_skew(expired.date_signed):
            return None
        try:
            raw = serializer.loads(token)
        except BadSignature:
            return None
    except BadSignature:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def _within_clock_skew(signed_at: datetime | None) -> bool:
    """Whether a token was stamped in the near future rather than long ago.

    Only the future side is forgiven. A token whose age is positive and beyond
    `session_max_age` has genuinely expired, and stays refused.
    """
    if signed_at is None:
        return False
    ahead = (signed_at - datetime.now(UTC)).total_seconds()
    return 0 < ahead <= MAX_CLOCK_SKEW_SECONDS
