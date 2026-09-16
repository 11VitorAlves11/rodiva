import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    context: dict[str, str] | None
    entity_type: str
    entity_id: uuid.UUID | None
    vehicle_id: uuid.UUID | None
    created_at: datetime
    read_at: datetime | None

    model_config = {"from_attributes": True}


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    unread: int


class PreferenceIn(BaseModel):
    channel_inapp: bool = True
    channel_email: bool = False
    min_urgency: Literal["overdue", "very_urgent", "urgent", "upcoming", "future"] = "urgent"
    vehicle_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    quiet_hours_start: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_end: int | None = Field(default=None, ge=0, le=23)

    @model_validator(mode="after")
    def quiet_hours_are_a_window(self) -> Self:
        if (self.quiet_hours_start is None) != (self.quiet_hours_end is None):
            raise ValueError("Quiet hours need both a start and an end")
        return self


class PreferenceOut(PreferenceIn):
    model_config = {"from_attributes": True}


class EvaluationOut(BaseModel):
    created: int
    delivered: int
    failed: int
