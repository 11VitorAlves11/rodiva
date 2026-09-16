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

    cors_origins: list[str] = ["http://localhost:5173"]

    # Household defaults applied to a newly created household (RF-ADM-001).
    default_locale: str = "pt-PT"
    default_currency: str = "EUR"
    default_distance_unit: Literal["km", "mi"] = "km"
    default_timezone: str = "Europe/Lisbon"

    storage_path: str = "/storage"
    upload_max_bytes: int = 20 * 1024 * 1024

    @property
    def cookies_secure(self) -> bool:
        """Session cookies are HTTPS-only everywhere except local development."""
        return self.environment == "prod"

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
