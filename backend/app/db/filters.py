"""Helpers for keeping soft-deleted rows out of ordinary reads."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ColumnElement

from app.models.mixins import SoftDelete


def active(model: type[SoftDelete]) -> ColumnElement[bool]:
    """The clause every read of a soft-deletable table needs.

    Written as a helper rather than repeated inline so a missing filter is easy
    to spot: a query on one of these tables either mentions `active(...)` or is
    deliberately looking at deleted rows.
    """
    return model.deleted_at.is_(None)


def mark_deleted(row: SoftDelete, actor_id: uuid.UUID | None) -> None:
    row.deleted_at = datetime.now(UTC)
    row.deleted_by = actor_id


def mark_restored(row: SoftDelete) -> None:
    row.deleted_at = None
    row.deleted_by = None
