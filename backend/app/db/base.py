"""Metadata aggregator: importing this module registers every table on `Base`.

Alembic's autogenerate and the test fixtures rely on it, so a new model is only
ever added to `app/models/__init__.py`.
"""

from app.models import (
    Attachment,
    Base,
    ExpenseRecord,
    FuelRecord,
    Household,
    Membership,
    Note,
    OdometerReading,
    Reminder,
    User,
    Vehicle,
    WorkRecord,
)

__all__ = [
    "Attachment",
    "Base",
    "ExpenseRecord",
    "FuelRecord",
    "Household",
    "Membership",
    "Note",
    "OdometerReading",
    "Reminder",
    "User",
    "Vehicle",
    "WorkRecord",
]
