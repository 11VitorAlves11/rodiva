import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AttachmentIn(BaseModel):
    filename: str = Field(min_length=1, max_length=300)
    content_type: str
    content_base64: str


class AttachmentOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    filename: str
    content_type: str
    size: int
    checksum: str
    created_at: datetime

    model_config = {"from_attributes": True}
