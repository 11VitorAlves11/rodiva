import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

WorkKind = Literal["maintenance", "repair", "modification"]

#: RF-INT-009: the parts must add up to the total, but an invoice rounds and a
#: cent either way is not a mistake worth refusing a record over.
COST_TOLERANCE = Decimal("0.02")


class WorkRecordItemIn(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    quantity: Decimal = Field(default=Decimal("1"), gt=0, max_digits=10, decimal_places=3)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)


class WorkRecordItemOut(WorkRecordItemIn):
    id: uuid.UUID
    position: int

    model_config = {"from_attributes": True}


class WorkRecordIn(BaseModel):
    recorded_on: date
    kind: WorkKind
    description: str = Field(min_length=1, max_length=500)
    odometer_reading: int | None = Field(default=None, ge=0, le=9_999_999)
    total_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    labour_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    parts_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    tax_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    discount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    supplier: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2_000)
    items: list[WorkRecordItemIn] = Field(default_factory=list, max_length=100)


class WorkRecordUpdate(BaseModel):
    recorded_on: date | None = None
    kind: WorkKind | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    odometer_reading: int | None = Field(default=None, ge=0, le=9_999_999)
    total_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    labour_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    parts_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    tax_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    discount: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    supplier: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2_000)
    #: Omitted leaves the lines alone; given, it replaces them wholesale.
    items: list[WorkRecordItemIn] | None = Field(default=None, max_length=100)


class WorkRecordOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    recorded_on: date
    kind: WorkKind
    description: str
    odometer_reading: int | None
    total_cost: Decimal | None
    labour_cost: Decimal | None
    parts_cost: Decimal | None
    tax_cost: Decimal | None
    discount: Decimal | None
    supplier: str | None
    notes: str | None
    items: list[WorkRecordItemOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
