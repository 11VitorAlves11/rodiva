import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import SoftDelete


class FuelRecord(Base, SoftDelete):
    """Fuel fill-up and its calculated consumption (spec §8.1)."""

    __tablename__ = "fuel_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    odometer_reading: Mapped[int | None] = mapped_column()
    volume_litres: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    fuel_type: Mapped[str | None] = mapped_column(String(50))
    station: Mapped[str | None] = mapped_column(String(200))
    full_tank: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    excluded_from_consumption: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consumption_l_per_100km: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    notes: Mapped[str | None] = mapped_column(String(2_000))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
