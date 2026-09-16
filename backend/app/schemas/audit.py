import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    actor_label: str
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    summary: str
    context: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditPage(BaseModel):
    items: list[AuditEventOut]
    # Cursor for the next page: the created_at of the last row returned. Null
    # when the listing reached the end.
    next_before: datetime | None
