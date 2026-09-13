import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import VehicleStatus


class VehicleIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    license_plate: str | None = None
    vin: str | None = None
    distance_unit: str = Field(default="km", pattern="^(km|mi)$")


class VehicleOut(BaseModel):
    id: uuid.UUID
    name: str
    type: str | None
    make: str | None
    model: str | None
    year: int | None
    license_plate: str | None
    vin: str | None
    photo_url: str | None
    distance_unit: str
    status: VehicleStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VehiclePhotoIn(BaseModel):
    content_base64: str
    content_type: str
