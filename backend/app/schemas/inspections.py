import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

FieldType = Literal["text", "number", "date", "single", "multiple", "boolean", "photo", "note"]


class InspectionField(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$", max_length=80)
    label: str = Field(min_length=1, max_length=200)
    type: FieldType
    required: bool = False
    options: list[str] = Field(default_factory=list, max_length=100)
    failure_values: list[str | bool] = Field(default_factory=list, max_length=100)
    create_plan_on_failure: bool = False

    @model_validator(mode="after")
    def options_match_type(self) -> "InspectionField":
        if self.type in {"single", "multiple"} and not self.options:
            raise ValueError("Selection fields require options")
        return self


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    vehicle_id: uuid.UUID | None = None
    fields: list[InspectionField] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_field_ids(self) -> "TemplateIn":
        ids = [field.id for field in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("Field identifiers must be unique")
        return self


class TemplateOut(TemplateIn):
    id: uuid.UUID
    household_id: uuid.UUID
    version: int
    archived: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectionIn(BaseModel):
    template_id: uuid.UUID
    recorded_on: date
    odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    responses: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=2_000)


class InspectionUpdate(BaseModel):
    recorded_on: date | None = None
    odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    responses: dict[str, Any] | None = None
    notes: str | None = Field(default=None, max_length=2_000)


class InspectionOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    template_id: uuid.UUID
    template_snapshot: dict[str, Any]
    responses: dict[str, Any]
    status: Literal["draft", "completed"]
    result: Literal["passed", "passed_with_observations", "failed"] | None
    recorded_on: date
    odometer: int | None
    notes: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
