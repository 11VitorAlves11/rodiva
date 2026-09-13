import enum

from sqlalchemy import Enum


def pg_enum(python_enum: type[enum.Enum], name: str) -> Enum:
    """A Postgres native enum, named explicitly so Alembic tracks it as a type."""
    return Enum(python_enum, name=name, values_callable=lambda e: [member.value for member in e])


class Role(enum.StrEnum):
    """Household member profile — see spec §2.2/§2.3 for the permission matrix."""

    OWNER = "owner"
    MANAGER = "manager"
    EDITOR = "editor"
    READER = "reader"


class VehicleStatus(enum.StrEnum):
    """Spec §5.1 "Estado": active, temporarily parked, sold, or archived."""

    ACTIVE = "active"
    PARKED = "parked"
    SOLD = "sold"
    ARCHIVED = "archived"
