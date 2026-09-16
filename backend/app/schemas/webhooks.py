import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class WebhookIn(BaseModel):
    description: str = Field(default="", max_length=100)
    url: HttpUrl
    # Empty means every event the household produces.
    events: list[str] = Field(default_factory=list, max_length=50)


class WebhookUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=100)
    url: HttpUrl | None = None
    events: list[str] | None = Field(default=None, max_length=50)
    active: bool | None = None


class WebhookOut(BaseModel):
    id: uuid.UUID
    description: str
    url: str
    events: list[str]
    active: bool
    created_at: datetime
    last_success_at: datetime | None
    last_error: str

    model_config = {"from_attributes": True}


class WebhookCreated(WebhookOut):
    # Shown once, at creation: the receiver needs it to verify the signature.
    secret: str


class WebhookDeliveryOut(BaseModel):
    id: uuid.UUID
    event: str
    payload: dict[str, Any]
    status: str
    attempts: int
    next_attempt_at: datetime
    response_status: int | None
    last_error: str
    created_at: datetime
    delivered_at: datetime | None

    model_config = {"from_attributes": True}
