import uuid
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field, model_validator


class FuelRecordIn(BaseModel):
    recorded_on: date
    odometer_reading: int | None = Field(default=None, ge=0, le=9_999_999)
    volume_litres: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    total_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=3)
    fuel_type: str | None = Field(default=None, max_length=50)
    station: str | None = Field(default=None, max_length=200)
    full_tank: bool = True
    excluded_from_consumption: bool = False
    notes: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def calculate_missing_price_value(self) -> "FuelRecordIn":
        values = (self.volume_litres, self.total_price, self.unit_price)
        if sum(value is not None for value in values) < 2:
            raise ValueError("Provide at least two of volume, total price and unit price")
        if self.volume_litres is None:
            assert self.total_price is not None and self.unit_price is not None
            if self.unit_price == 0:
                raise ValueError("Unit price cannot be zero when calculating volume")
            self.volume_litres = (self.total_price / self.unit_price).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
        elif self.total_price is None:
            assert self.unit_price is not None
            self.total_price = (self.volume_litres * self.unit_price).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        elif self.unit_price is None:
            self.unit_price = (self.total_price / self.volume_litres).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
        return self


class FuelRecordOut(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    recorded_on: date
    odometer_reading: int | None
    volume_litres: Decimal
    total_price: Decimal
    unit_price: Decimal
    fuel_type: str | None
    station: str | None
    full_tank: bool
    excluded_from_consumption: bool
    consumption_l_per_100km: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
