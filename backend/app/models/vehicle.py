import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import VehicleStatus, pg_enum
from app.models.mixins import SoftDelete


class Vehicle(Base, SoftDelete):
    """A vehicle, bike, trailer or other equipment tracked in the garage (spec §5)."""

    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str | None] = mapped_column(String(50))
    make: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    year: Mapped[int | None] = mapped_column(Integer)
    # RF-VEI-002: a matrícula (license plate) may be absent for bikes, machines
    # or trailers — a custom identifier stands in for it (RF-VEI-003).
    license_plate: Mapped[str | None] = mapped_column(String(20))
    vin: Mapped[str | None] = mapped_column(String(50))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    distance_unit: Mapped[str] = mapped_column(String(2), nullable=False, default="km")
    #: What the vehicle runs on (RF-VEI-005). Drives whether charging, fuel, or
    #: both make sense for it, and which unit its energy reads in.
    energy_type: Mapped[str] = mapped_column(String(20), nullable=False, default="petrol")
    #: The odometer the vehicle was first recorded at; distances are measured
    #: from here rather than from zero (RF-VEI-006).
    initial_odometer: Mapped[int | None] = mapped_column(Integer)
    #: A replaced or miscalibrated odometer reads off the real distance by a
    #: fixed amount or a fixed ratio; both are applied to new readings so the
    #: history stays comparable (RF-VEI-007).
    odometer_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    odometer_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), nullable=False, default=Decimal("1.0")
    )
    #: Manual position in the garage (RF-VEI-008); ties break on name.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Ownership, for duration and cost-of-ownership figures (RF-VEI-012).
    purchase_date: Mapped[date | None] = mapped_column(Date)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    purchase_odometer: Mapped[int | None] = mapped_column(Integer)
    sale_date: Mapped[date | None] = mapped_column(Date)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[VehicleStatus] = mapped_column(
        pg_enum(VehicleStatus, "vehicle_status"), nullable=False, default=VehicleStatus.ACTIVE
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
