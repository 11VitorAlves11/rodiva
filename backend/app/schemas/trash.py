import uuid
from datetime import datetime

from pydantic import BaseModel


class TrashItem(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    # Null for a vehicle, which is not kept against another one.
    vehicle_id: uuid.UUID | None
    summary: str
    deleted_at: datetime
    deleted_by: uuid.UUID | None
    deleted_by_label: str
