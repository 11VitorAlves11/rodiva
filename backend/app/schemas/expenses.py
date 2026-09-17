import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

#: RF-DES-007. "overdue" is never stored: it is what a pending record with a due
#: date in the past reads as, worked out when the record is read so it cannot go
#: stale while nobody is looking.
ExpenseStatus = Literal["planned", "pending", "paid", "cancelled"]
ExpenseStatusOut = Literal["planned", "pending", "paid", "cancelled", "overdue"]

RecurrenceUnit = Literal["day", "month", "year"]


class ExpenseRecordIn(BaseModel):
    issued_on: date
    category: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    supplier: str | None = Field(default=None, max_length=200)
    status: ExpenseStatus = "paid"
    due_on: date | None = None
    paid_on: date | None = None
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2_000)
    recurrence_interval: int | None = Field(default=None, ge=1, le=120)
    recurrence_unit: RecurrenceUnit | None = None
    recurrence_amount_varies: bool = False


class ExpenseRecordUpdate(BaseModel):
    issued_on: date | None = None
    category: str | None = Field(default=None, min_length=1, max_length=50)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    supplier: str | None = Field(default=None, max_length=200)
    status: ExpenseStatus | None = None
    due_on: date | None = None
    paid_on: date | None = None
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2_000)
    recurrence_interval: int | None = Field(default=None, ge=1, le=120)
    recurrence_unit: RecurrenceUnit | None = None
    recurrence_amount_varies: bool | None = None


class ExpenseRecordOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    issued_on: date
    category: str
    amount: Decimal
    supplier: str | None
    status: ExpenseStatusOut
    due_on: date | None
    paid_on: date | None
    reference: str | None
    notes: str | None
    recurrence_interval: int | None
    recurrence_unit: RecurrenceUnit | None
    recurrence_amount_varies: bool
    recurrence_parent_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
