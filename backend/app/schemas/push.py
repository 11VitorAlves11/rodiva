import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PushKey(BaseModel):
    enabled: bool
    public_key: str


class PushSubscriptionIn(BaseModel):
    #: The push service URL the browser handed out. Opaque and long.
    endpoint: str = Field(min_length=10, max_length=2_000)
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=100)


class PushSubscriptionOut(BaseModel):
    id: uuid.UUID
    endpoint: str
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}
