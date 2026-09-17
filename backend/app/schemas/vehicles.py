import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import VehicleStatus

#: What the vehicle runs on (RF-VEI-005). "other" carries bicycles, trailers and
#: anything else with no fuel of its own.
EnergyType = Literal["petrol", "diesel", "electric", "hybrid", "plugin_hybrid", "lpg", "other"]

#: A replaced odometer reads off by a fixed amount; a wrongly sized wheel reads
#: off by a ratio. Both are bounded so a typo cannot rewrite a whole history.
_MULTIPLIER = Field(default=Decimal("1.0"), gt=0, le=10, max_digits=6, decimal_places=4)
_OFFSET = Field(default=0, ge=-9_999_999, le=9_999_999)


class VehicleIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    license_plate: str | None = None
    vin: str | None = None
    distance_unit: str = Field(default="km", pattern="^(km|mi)$")
    energy_type: EnergyType = "petrol"
    initial_odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    odometer_offset: int = _OFFSET
    odometer_multiplier: Decimal = _MULTIPLIER
    sort_order: int = Field(default=0, ge=0, le=9_999)
    purchase_date: date | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    purchase_odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    sale_date: date | None = None
    sale_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class VehicleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    license_plate: str | None = None
    vin: str | None = None
    distance_unit: str | None = Field(default=None, pattern="^(km|mi)$")
    status: VehicleStatus | None = None
    energy_type: EnergyType | None = None
    initial_odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    odometer_offset: int | None = Field(default=None, ge=-9_999_999, le=9_999_999)
    odometer_multiplier: Decimal | None = Field(
        default=None, gt=0, le=10, max_digits=6, decimal_places=4
    )
    sort_order: int | None = Field(default=None, ge=0, le=9_999)
    purchase_date: date | None = None
    purchase_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    purchase_odometer: int | None = Field(default=None, ge=0, le=9_999_999)
    sale_date: date | None = None
    sale_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


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
    energy_type: str
    initial_odometer: int | None
    odometer_offset: int
    odometer_multiplier: Decimal
    sort_order: int
    purchase_date: date | None
    purchase_price: Decimal | None
    purchase_odometer: int | None
    sale_date: date | None
    sale_price: Decimal | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VehiclePhotoIn(BaseModel):
    content_base64: str
    content_type: str


class VehicleOrderIn(BaseModel):
    """The garage's order, as the member dragged it (RF-VEI-008)."""

    vehicle_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
