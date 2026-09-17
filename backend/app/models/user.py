import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """An account, signed in with a password or through the household's provider."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    #: Empty for an account that only ever signs in through OIDC: there is no
    #: password to check, and an empty hash can never match one.
    password_hash: Mapped[str] = mapped_column(String, nullable=False, default="")
    #: The provider's stable identifier for this person (RF-AUT-006). Unique so
    #: two accounts can never claim the same subject.
    oidc_subject: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String)
    # RF-AUT-009: per-user preferences, distinct from the household defaults.
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="pt-PT")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Europe/Lisbon")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
