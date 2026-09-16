import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

EquipmentKind = Literal["tires", "trailer", "roof_rack", "accessory", "other"]
EquipmentStatus = Literal["mounted", "unmounted", "stored", "sold", "discarded"]


class EquipmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: EquipmentKind
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    tire_size: str | None = Field(default=None, max_length=50)
    tire_dot: str | None = Field(default=None, max_length=20)
    tread_depth_mm: Decimal | None = Field(default=None, ge=0, le=30)
    season: Literal["summer", "winter", "all_season"] | None = None
    notes: str | None = Field(default=None, max_length=2_000)


class EquipmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: EquipmentKind | None = None
    status: Literal["unmounted", "stored", "sold", "discarded"] | None = None
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    tire_size: str | None = Field(default=None, max_length=50)
    tire_dot: str | None = Field(default=None, max_length=20)
    tread_depth_mm: Decimal | None = Field(default=None, ge=0, le=30)
    season: Literal["summer", "winter", "all_season"] | None = None
    notes: str | None = Field(default=None, max_length=2_000)


class EquipmentOut(EquipmentIn):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    status: EquipmentStatus
    positions: dict[str, Any] | None
    distance_accumulated: int
    open_reminders_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MountIn(BaseModel):
    on: date
    odometer: int = Field(ge=0, le=9_999_999)
    positions: dict[str, str] | None = None


class MountPeriodOut(BaseModel):
    id: uuid.UUID
    equipment_id: uuid.UUID
    mounted_on: date
    mounted_odometer: int
    unmounted_on: date | None
    unmounted_odometer: int | None
    distance: int
    positions: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RotationIn(BaseModel):
    on: date
    odometer: int = Field(ge=0, le=9_999_999)
    positions: dict[str, str]


class RotationOut(BaseModel):
    id: uuid.UUID
    equipment_id: uuid.UUID
    rotated_on: date
    odometer: int
    positions: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
