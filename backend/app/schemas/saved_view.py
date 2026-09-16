import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SavedViewIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    query: dict[str, Any]


class SavedViewOut(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    query: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
