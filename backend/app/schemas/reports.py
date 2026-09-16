import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class CategoryTotal(BaseModel):
    category: str
    amount: Decimal


class MonthlyTotal(BaseModel):
    month: str
    charging: Decimal = Decimal(0)
    fuel: Decimal
    work: Decimal
    expenses: Decimal
    total: Decimal
    distance: int


class VehicleReport(BaseModel):
    vehicle_id: uuid.UUID
    vehicle_name: str
    distance_unit: str
    total_cost: Decimal
    distance: int
    cost_per_distance: Decimal | None
    consumption_average: Decimal | None
    consumption_minimum: Decimal | None
    consumption_maximum: Decimal | None
    categories: list[CategoryTotal]
    monthly: list[MonthlyTotal]


class ReportSummary(BaseModel):
    date_from: date | None
    date_to: date | None
    currency: str
    total_cost: Decimal
    total_distance: int
    inventory_value: Decimal
    overdue_reminders: int
    vehicles: list[VehicleReport]
