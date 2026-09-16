"""Password hashing and signed identifiers for server-side sessions."""

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
GOOGLE_OAUTH_STATE_SALT = "rodiva.google_oauth_state"
#: The OAuth round trip to Google and back should take seconds, not minutes —
#: keep the state token's window tight since it's the CSRF binding for the flow.
GOOGLE_OAUTH_STATE_MAX_AGE = 60 * 10


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


def issue_session(session_id: uuid.UUID) -> str:
    return _serializer().dumps(str(session_id))


def read_session(token: str) -> uuid.UUID | None:
    """Return the session id carried by a valid, unexpired token, else None."""
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


def issue_google_oauth_state(user_id: uuid.UUID) -> str:
    """Sign a short-lived token binding a Google OAuth round trip to a user (RF-GCAL-001)."""
    serializer = URLSafeTimedSerializer(get_settings().secret_key, salt=GOOGLE_OAUTH_STATE_SALT)
    return serializer.dumps(str(user_id))


def read_google_oauth_state(token: str) -> uuid.UUID | None:
    """Return the user id bound to a valid, unexpired OAuth state token, else None."""
    serializer = URLSafeTimedSerializer(get_settings().secret_key, salt=GOOGLE_OAUTH_STATE_SALT)
    try:
        raw = serializer.loads(token, max_age=GOOGLE_OAUTH_STATE_MAX_AGE)
    except (BadSignature, SignatureExpired):
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
