"""Validating and storing custom field values (RF-ADM-007/008)."""

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomFieldDefinition, CustomFieldValue

#: What a secret reads as once stored. The real value is never sent back, so a
#: credential parked in a custom field does not leak through an ordinary read.
SECRET_MASK = "••••••••"


class FieldError(ValueError):
    """A value that does not fit the field it was sent for."""


async def definitions_for(
    kind: str, household_id: uuid.UUID, db: AsyncSession, *, include_archived: bool = False
) -> list[CustomFieldDefinition]:
    query = select(CustomFieldDefinition).where(
        CustomFieldDefinition.household_id == household_id,
        CustomFieldDefinition.record_kind == kind,
    )
    if not include_archived:
        query = query.where(CustomFieldDefinition.archived.is_(False))
    rows = await db.scalars(
        query.order_by(CustomFieldDefinition.position, CustomFieldDefinition.key)
    )
    return list(rows)


def coerce(definition: CustomFieldDefinition, raw: Any) -> Any:
    """Return `raw` in the shape the field's type calls for, or raise."""
    if raw is None or raw == "":
        return None
    kind = definition.field_type
    if kind in {"text", "secret"}:
        return str(raw)
    if kind == "url":
        value = str(raw)
        if not value.startswith(("http://", "https://")):
            raise FieldError(f"{definition.label} must be a http:// or https:// address")
        return value
    if kind in {"number", "currency"}:
        try:
            return str(Decimal(str(raw)))
        except (InvalidOperation, ValueError) as exc:
            raise FieldError(f"{definition.label} must be a number") from exc
    if kind == "date":
        try:
            return date.fromisoformat(str(raw)).isoformat()
        except ValueError as exc:
            raise FieldError(f"{definition.label} must be a date") from exc
    if kind == "checkbox":
        return bool(raw)
    if kind == "choice":
        if str(raw) not in definition.options:
            raise FieldError(f"{definition.label} does not offer {raw}")
        return str(raw)
    if kind == "multi_choice":
        if not isinstance(raw, list):
            raise FieldError(f"{definition.label} takes a list of options")
        unknown = [one for one in raw if str(one) not in definition.options]
        if unknown:
            raise FieldError(f"{definition.label} does not offer {', '.join(map(str, unknown))}")
        return [str(one) for one in raw]
    raise FieldError(f"Unknown field type: {kind}")


def validate(definitions: list[CustomFieldDefinition], submitted: dict[str, Any]) -> dict[str, Any]:
    """Check a whole submission and return what should be stored.

    Keys with no definition are dropped rather than refused: a form left open in
    another tab while a field was archived should still save the rest.
    """
    by_key = {definition.key: definition for definition in definitions}
    stored: dict[str, Any] = {}
    for key, raw in submitted.items():
        definition = by_key.get(key)
        if definition is None:
            continue
        # A masked secret means "leave it as it was", not "set it to bullets".
        if definition.field_type == "secret" and raw == SECRET_MASK:
            continue
        value = coerce(definition, raw)
        if value is not None:
            stored[key] = value
    missing = [
        definition.label
        for definition in definitions
        if definition.required and stored.get(definition.key) in (None, "", [])
    ]
    if missing:
        raise FieldError(f"Required: {', '.join(missing)}")
    return stored


def for_display(definitions: list[CustomFieldDefinition], stored: dict[str, Any]) -> dict[str, Any]:
    """The values as they should be read back, with secrets masked."""
    secrets = {d.key for d in definitions if d.field_type == "secret"}
    return {
        key: (SECRET_MASK if key in secrets and value else value) for key, value in stored.items()
    }


async def values_for(kind: str, record_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    row = await db.scalar(
        select(CustomFieldValue).where(
            CustomFieldValue.record_kind == kind, CustomFieldValue.record_id == record_id
        )
    )
    return dict(row.values) if row else {}


async def store(kind: str, record_id: uuid.UUID, values: dict[str, Any], db: AsyncSession) -> None:
    """Merge `values` into the record's document, keeping untouched keys."""
    row = await db.scalar(
        select(CustomFieldValue).where(
            CustomFieldValue.record_kind == kind, CustomFieldValue.record_id == record_id
        )
    )
    if row is None:
        db.add(CustomFieldValue(record_kind=kind, record_id=record_id, values=values))
        return
    # Reassigned rather than mutated: SQLAlchemy does not see an in-place change
    # to a JSONB dict, and the update would be silently dropped.
    row.values = {**row.values, **values}
