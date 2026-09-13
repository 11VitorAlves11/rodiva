import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

ExpenseStatus = Literal["planned", "pending", "paid", "cancelled"]


class ExpenseRecordIn(BaseModel):
    issued_on: date
    category: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    supplier: str | None = Field(default=None, max_length=200)
    status: ExpenseStatus = "paid"


class ExpenseRecordUpdate(BaseModel):
    issued_on: date | None = None
    category: str | None = Field(default=None, min_length=1, max_length=50)
    amount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    supplier: str | None = Field(default=None, max_length=200)
    status: ExpenseStatus | None = None


class ExpenseRecordOut(ExpenseRecordIn):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
