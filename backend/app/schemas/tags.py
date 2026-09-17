import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.services import tags as tag_service

#: Matches the column; long enough to read as a label, short enough to stay a chip.
NAME = Field(min_length=1, max_length=50)
COLOUR = Field(default="#6B7280", max_length=7)


def _check_colour(value: str) -> str:
    if not tag_service.is_valid_colour(value):
        raise ValueError("colour must be a hex value such as #B94A22")
    return value


class TagIn(BaseModel):
    name: str = NAME
    color: str = COLOUR

    _colour = field_validator("color")(_check_colour)


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, max_length=7)

    @field_validator("color")
    @classmethod
    def _colour(cls, value: str | None) -> str | None:
        return None if value is None else _check_colour(value)


class TagOut(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TagUsage(TagOut):
    """A tag plus how many records carry it, for the management screen."""

    record_count: int


class RecordTagsIn(BaseModel):
    """The full set of tags a record should carry after the call."""

    tag_ids: list[uuid.UUID] = Field(default_factory=list, max_length=25)
