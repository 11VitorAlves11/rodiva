import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import SoftDelete


class ExpenseRecord(Base, SoftDelete):
    __tablename__ = "expense_records"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    issued_on: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(50))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    supplier: Mapped[str | None] = mapped_column(String(200))
    #: planned, pending, paid, cancelled or overdue (RF-DES-007). Overdue is
    #: derived on read from a due date that has passed, never stored, so it
    #: cannot go stale while nobody is looking.
    status: Mapped[str] = mapped_column(String(20), default="paid")
    #: When it falls due and when it was actually settled (RF-DES-002).
    due_on: Mapped[date | None] = mapped_column(Date, index=True)
    paid_on: Mapped[date | None] = mapped_column(Date)
    #: Invoice or policy number, so a record can be matched to paperwork.
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(String(2_000))
    #: Recurrence (RF-DES-004): every `recurrence_interval` days, months or
    #: years. Null unit means the expense does not repeat.
    recurrence_interval: Mapped[int | None] = mapped_column(Integer)
    recurrence_unit: Mapped[str | None] = mapped_column(String(10))
    #: RF-DES-005: for a bill whose amount changes each time, the next
    #: occurrence is raised pending and with no amount copied over.
    recurrence_amount_varies: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: The record this one was generated from, so a chain can be followed back.
    recurrence_parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("expense_records.id", ondelete="SET NULL")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
