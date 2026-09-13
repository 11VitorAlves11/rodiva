import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Household(Base):
    """The sharing boundary (spec §2.1): vehicles, tags and settings belong here."""

    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="pt-PT")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    distance_unit: Mapped[str] = mapped_column(String(2), nullable=False, default="km")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Europe/Lisbon")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
