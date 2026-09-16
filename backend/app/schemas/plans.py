import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

PlanStage = Literal["planned", "in_progress", "testing", "completed"]
PlanPriority = Literal["low", "normal", "high", "urgent"]
PlanKind = Literal["maintenance", "repair", "modification"]


class InventoryUse(BaseModel):
    item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)


class PlanIn(BaseModel):
    kind: PlanKind
    description: str = Field(min_length=1, max_length=500)
    priority: PlanPriority = "normal"
    stage: Literal["planned", "in_progress", "testing"] = "planned"
    estimated_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    due_date: date | None = None
    due_odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    notes: str | None = Field(default=None, max_length=2_000)


class PlanUpdate(BaseModel):
    kind: PlanKind | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    priority: PlanPriority | None = None
    stage: Literal["planned", "in_progress", "testing"] | None = None
    estimated_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    due_date: date | None = None
    due_odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    notes: str | None = Field(default=None, max_length=2_000)


class PlanComplete(BaseModel):
    recorded_on: date
    odometer_reading: int = Field(ge=0, le=9_999_999)
    total_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    supplier: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2_000)
    inventory_items: list[InventoryUse] = Field(default_factory=list, max_length=100)


class PlanOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    stage: PlanStage
    kind: PlanKind
    priority: PlanPriority
    description: str
    estimated_cost: Decimal | None
    due_date: date | None
    due_odometer: int | None
    notes: str | None
    completed_work_record_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
