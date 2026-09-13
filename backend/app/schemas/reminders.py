import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Urgency = Literal["future", "upcoming", "urgent", "very_urgent", "overdue", "completed"]


class ReminderIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    due_date: date | None = None
    due_odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    repeat_days: int | None = Field(default=None, ge=1, le=36_500)
    repeat_distance: int | None = Field(default=None, ge=1, le=9_999_999)
    notes: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def needs_a_due_condition(self) -> "ReminderIn":
        if self.due_date is None and self.due_odometer is None:
            raise ValueError("A reminder needs a due date or odometer value")
        return self


class ReminderOut(ReminderIn):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    status: str
    urgency: Urgency
    completed_at: datetime | None
    created_at: datetime
