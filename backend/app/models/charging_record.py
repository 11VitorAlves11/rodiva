import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChargingRecord(Base):
    __tablename__ = "charging_records"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    recorded_on: Mapped[date] = mapped_column(Date)
    odometer_reading: Mapped[int | None] = mapped_column()
    energy_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    soc_start: Mapped[int | None] = mapped_column()
    soc_end: Mapped[int | None] = mapped_column()
    location: Mapped[str | None] = mapped_column(String(200))
    charger_type: Mapped[str] = mapped_column(String(100), default="home")
    notes: Mapped[str | None] = mapped_column(String(2000))
    efficiency_kwh_per_100km: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
