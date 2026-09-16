import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

MovementKind = Literal["entry", "adjustment", "requisition", "return", "removal"]


class InventoryItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    vehicle_id: uuid.UUID | None = None
    reference: str | None = Field(default=None, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=100)
    quantity: Decimal = Field(default=Decimal(0), ge=0, max_digits=12, decimal_places=3)
    unit: str = Field(default="unit", min_length=1, max_length=30)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    minimum_quantity: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    location: str | None = Field(default=None, max_length=200)
    supplier: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2_000)


class InventoryItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    vehicle_id: uuid.UUID | None = None
    reference: str | None = Field(default=None, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    minimum_quantity: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=3)
    location: str | None = Field(default=None, max_length=200)
    supplier: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2_000)


class InventoryItemOut(InventoryItemIn):
    id: uuid.UUID
    household_id: uuid.UUID
    low_stock: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StockMovementIn(BaseModel):
    kind: MovementKind
    quantity: Decimal = Field(max_digits=12, decimal_places=3)
    work_record_id: uuid.UUID | None = None
    plan_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=500)


class StockMovementOut(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    kind: MovementKind
    quantity_delta: Decimal
    quantity_after: Decimal
    work_record_id: uuid.UUID | None
    plan_id: uuid.UUID | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
