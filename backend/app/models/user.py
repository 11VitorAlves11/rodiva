import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """A local account (email + password). OIDC subjects arrive in a later phase."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    # RF-AUT-009: per-user preferences, distinct from the household defaults.
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="pt-PT")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Europe/Lisbon")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
