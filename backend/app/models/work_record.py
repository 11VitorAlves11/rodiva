import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    #: What the total is made of (RF-INT-002). Kept alongside the total rather
    #: than replacing it: plenty of invoices only ever give one number, and
    #: forcing a breakdown would mean inventing figures nobody has.
    labour_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    parts_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    tax_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    discount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    supplier: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(String(2_000))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    items: Mapped[list["WorkRecordItem"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        order_by="WorkRecordItem.position",
        lazy="selectin",
    )


class WorkRecordItem(Base):
    """One line of a work record: a task done or a part fitted (RF-INT-003).

    Quantity times unit cost gives the line's own cost, so an invoice with four
    tyres and an alignment reads as four tyres and an alignment rather than one
    opaque total.
    """

    __tablename__ = "work_record_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    work_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    #: Position as the member ordered them, so a line list keeps its sequence.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record: Mapped["WorkRecord"] = relationship(back_populates="items")
