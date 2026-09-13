import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class OdometerReadingIn(BaseModel):
    recorded_on: date
    reading: int = Field(ge=0, le=9_999_999)
    start_reading: int | None = Field(default=None, ge=0, le=9_999_999)
    is_adjustment: bool = False
    notes: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def start_cannot_exceed_end(self) -> "OdometerReadingIn":
        if self.start_reading is not None and self.start_reading > self.reading:
            raise ValueError("Start reading cannot exceed the final reading")
        return self


class OdometerReadingOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    recorded_on: date
    reading: int
    start_reading: int | None
    distance: int | None
    is_adjustment: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OdometerReadingUpdate(BaseModel):
    recorded_on: date | None = None
    reading: int | None = Field(default=None, ge=0, le=9_999_999)
    start_reading: int | None = Field(default=None, ge=0, le=9_999_999)
    is_adjustment: bool | None = None
    notes: str | None = Field(default=None, max_length=2_000)
