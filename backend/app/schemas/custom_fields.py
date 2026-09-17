import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

FieldType = Literal[
    "text", "number", "currency", "date", "choice", "multi_choice", "checkbox", "url", "secret"
]


class CustomFieldIn(BaseModel):
    record_kind: str = Field(min_length=1, max_length=20)
    key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=100)
    field_type: FieldType
    required: bool = False
    options: list[str] = Field(default_factory=list, max_length=50)
    position: int = Field(default=0, ge=0, le=999)

    @model_validator(mode="after")
    def _choices_need_options(self) -> "CustomFieldIn":
        if self.field_type in {"choice", "multi_choice"} and not self.options:
            raise ValueError("A choice field needs at least one option")
        return self


class CustomFieldUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    required: bool | None = None
    options: list[str] | None = Field(default=None, max_length=50)
    position: int | None = Field(default=None, ge=0, le=999)
    archived: bool | None = None


class CustomFieldOut(BaseModel):
    id: uuid.UUID
    record_kind: str
    key: str
    label: str
    field_type: FieldType
    required: bool
    options: list[str]
    position: int
    archived: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomFieldValuesIn(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
