import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ChargingIn(BaseModel):
    recorded_on: date
    odometer_reading: int | None = Field(default=None, ge=0, le=9_999_999)
    energy_kwh: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    total_cost: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    soc_start: int | None = Field(default=None, ge=0, le=100)
    soc_end: int | None = Field(default=None, ge=0, le=100)
    location: str | None = Field(default=None, max_length=200)
    charger_type: str = Field(default="home", min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_soc(self) -> "ChargingIn":
        if (
            self.soc_start is not None
            and self.soc_end is not None
            and self.soc_end < self.soc_start
        ):
            raise ValueError("Final state of charge cannot be lower than initial state")
        return self


class ChargingOut(ChargingIn):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    unit_price: Decimal
    efficiency_kwh_per_100km: Decimal | None
    created_at: datetime
    model_config = {"from_attributes": True}
