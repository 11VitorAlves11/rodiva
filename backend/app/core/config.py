import secrets
from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Rodiva"
    environment: Literal["dev", "prod", "test"] = "dev"

    database_url: str = "postgresql+asyncpg://rodiva:rodiva@localhost:5432/rodiva"

    # Local-only for now (RF-AUT-001). OIDC is deferred to the parity phase
    # (RF-AUT-006) — the literal is kept narrow on purpose so a config typo
    # fails at startup instead of silently falling back to local auth.
    auth_mode: Literal["local"] = "local"
    allow_public_registration: bool = True

    # Signs the session cookie. Rotating it logs everyone out, which is the point.
    secret_key: str = ""
    session_cookie_name: str = "rodiva_session"
    session_max_age: int = 60 * 60 * 24 * 14

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True

    # How often the API evaluates reminders and flushes the delivery queue
    # (RF-NOT-005). Zero turns the in-process schedule off, for deployments
    # driving POST /api/v1/notifications/run from their own scheduler.
    notification_interval_seconds: int = 900

    cors_origins: list[str] = ["http://localhost:5173"]

    # Household defaults applied to a newly created household (RF-ADM-001).
    default_locale: str = "pt-PT"
    default_currency: str = "EUR"
    default_distance_unit: Literal["km", "mi"] = "km"
    default_timezone: str = "Europe/Lisbon"

    storage_path: str = "/storage"
    upload_max_bytes: int = 20 * 1024 * 1024

    # RF-GCAL-001/007: OAuth credentials for the Google Calendar integration.
    # Unset by default — the feature stays inactive until a server operator
    # registers a Google Cloud OAuth client and sets these.
    google_client_id: str = ""
    google_client_secret: str = ""
    # Absolute, pre-registered URL Google redirects back to after consent —
    # must match the API's own origin (it serves /calendar/google/callback).
    public_base_url: str = "http://localhost:8000"
    # The frontend's origin, used only to build the link the OAuth callback
    # redirects to and the "open in Rodiva" link inside synced events. Kept
    # separate from public_base_url because the API and the SPA run on
    # different ports/origins in dev (:8000 vs :5173) and may well differ in
    # prod too (reverse-proxied API path vs. static site host).
    public_frontend_url: str = "http://localhost:5173"

    @property
    def cookies_secure(self) -> bool:
        """Session cookies are HTTPS-only everywhere except local development."""
        return self.environment == "prod"

    @property
    def google_calendar_enabled(self) -> bool:
        """Whether an operator has configured real Google OAuth credentials."""
        return bool(self.google_client_id and self.google_client_secret)

    @model_validator(mode="after")
    def _check_secrets(self) -> Self:
        if not self.secret_key:
            if self.environment == "prod":
                raise ValueError("SECRET_KEY is required when ENVIRONMENT=prod")
            # Dev/test convenience: sessions simply do not survive a restart.
            self.secret_key = secrets.token_urlsafe(32)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
