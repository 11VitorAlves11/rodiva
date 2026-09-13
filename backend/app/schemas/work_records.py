import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

WorkKind = Literal["maintenance", "repair", "modification"]


class WorkRecordIn(BaseModel):
    recorded_on: date
    kind: WorkKind
    description: str = Field(min_length=1, max_length=500)
    odometer_reading: int | None = Field(default=None, ge=0, le=9_999_999)
    total_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    supplier: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2_000)


class WorkRecordOut(WorkRecordIn):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
