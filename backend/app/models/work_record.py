import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import SoftDelete


class WorkRecord(Base, SoftDelete):
    """Preventive maintenance, repair, or modification (spec §9)."""

    __tablename__ = "work_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    odometer_reading: Mapped[int | None] = mapped_column(Integer)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    supplier: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(2_000))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
