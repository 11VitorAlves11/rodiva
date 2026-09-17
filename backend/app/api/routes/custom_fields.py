"""Defining custom fields and storing their values (RF-ADM-007/008, RF-VEI-014)."""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, DbSession
from app.api.routes.tags import _record_in_household
from app.models import CUSTOM_FIELD_KINDS, CustomFieldDefinition, Role
from app.schemas.custom_fields import (
    CustomFieldIn,
    CustomFieldOut,
    CustomFieldUpdate,
    CustomFieldValuesIn,
)
from app.services import custom_fields as service

router = APIRouter(prefix="/custom-fields", tags=["custom fields"])

# Defining a field reshapes every form in the household, so it stays with the
# managing roles; filling one in is ordinary editing (spec §2.3).
_CAN_MANAGE = {Role.OWNER, Role.MANAGER}
_CAN_FILL = {Role.OWNER, Role.MANAGER, Role.EDITOR}


def _known_kind(kind: str) -> None:
    if kind not in CUSTOM_FIELD_KINDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown record kind: {kind}"
        )


@router.get("", response_model=list[CustomFieldOut])
async def list_definitions(
    membership: CurrentMembership,
    db: DbSession,
    record_kind: str | None = None,
    include_archived: bool = False,
) -> list[CustomFieldDefinition]:
    query = select(CustomFieldDefinition).where(
        CustomFieldDefinition.household_id == membership.household_id
    )
    if record_kind:
        _known_kind(record_kind)
        query = query.where(CustomFieldDefinition.record_kind == record_kind)
    if not include_archived:
        query = query.where(CustomFieldDefinition.archived.is_(False))
    rows = await db.scalars(
        query.order_by(
            CustomFieldDefinition.record_kind,
            CustomFieldDefinition.position,
            CustomFieldDefinition.key,
        )
    )
    return list(rows)


@router.post("", response_model=CustomFieldOut, status_code=status.HTTP_201_CREATED)
async def create_definition(
    payload: CustomFieldIn, membership: CurrentMembership, db: DbSession
) -> CustomFieldDefinition:
    if membership.role not in _CAN_MANAGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot manage custom fields"
        )
    _known_kind(payload.record_kind)
    clash = await db.scalar(
        select(CustomFieldDefinition).where(
            CustomFieldDefinition.household_id == membership.household_id,
            CustomFieldDefinition.record_kind == payload.record_kind,
            CustomFieldDefinition.key == payload.key,
        )
    )
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A field keyed {payload.key} already exists for {payload.record_kind}",
        )
    definition = CustomFieldDefinition(household_id=membership.household_id, **payload.model_dump())
    db.add(definition)
    await db.commit()
    await db.refresh(definition)
    return definition


async def _definition(
    field_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> CustomFieldDefinition:
    definition = await db.get(CustomFieldDefinition, field_id)
    if definition is None or definition.household_id != membership.household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    return definition


@router.patch("/{field_id}", response_model=CustomFieldOut)
async def update_definition(
    field_id: uuid.UUID,
    payload: CustomFieldUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> CustomFieldDefinition:
    """Change a field's label, options, order, or whether it still appears.

    The key and the type are fixed once created: both would orphan or
    misinterpret every value already stored under them.
    """
    if membership.role not in _CAN_MANAGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot manage custom fields"
        )
    definition = await _definition(field_id, membership, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(definition, key, value)
    await db.commit()
    await db.refresh(definition)
    return definition


@router.get("/records/{kind}/{record_id}")
async def read_values(
    kind: str, record_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> dict[str, object]:
    _known_kind(kind)
    await _record_in_household(kind, record_id, membership, db)
    definitions = await service.definitions_for(kind, membership.household_id, db)
    stored = await service.values_for(kind, record_id, db)
    return service.for_display(definitions, stored)


@router.put("/records/{kind}/{record_id}")
async def write_values(
    kind: str,
    record_id: uuid.UUID,
    payload: CustomFieldValuesIn,
    membership: CurrentMembership,
    db: DbSession,
) -> dict[str, object]:
    _known_kind(kind)
    if membership.role not in _CAN_FILL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot edit records"
        )
    await _record_in_household(kind, record_id, membership, db)
    definitions = await service.definitions_for(kind, membership.household_id, db)
    try:
        cleaned = service.validate(definitions, payload.values)
    except service.FieldError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    await service.store(kind, record_id, cleaned, db)
    await db.commit()
    stored = await service.values_for(kind, record_id, db)
    return service.for_display(definitions, stored)
