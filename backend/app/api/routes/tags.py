"""Household tags and the records they sit on (RF-DOC-009, RF-PES-001, RF-REL-002)."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.models import (
    TAGGABLE_KINDS,
    ExpenseRecord,
    FuelRecord,
    Inspection,
    Note,
    OdometerReading,
    Plan,
    RecordTag,
    Role,
    Tag,
    Vehicle,
    WorkRecord,
)
from app.schemas.tags import RecordTagsIn, TagIn, TagOut, TagUpdate, TagUsage
from app.services import tags as tag_service

router = APIRouter(prefix="/tags", tags=["tags"])

# Tags are shared furniture for the whole household, so renaming or deleting one
# reaches every record at once — that stays with the roles that manage the
# household (spec §2.3). Putting an existing tag on a record is ordinary editing.
_CAN_MANAGE = {Role.OWNER, Role.MANAGER}
_CAN_TAG = {Role.OWNER, Role.MANAGER, Role.EDITOR}

_MODELS: dict[str, type[Any]] = {
    "vehicle": Vehicle,
    "odometer": OdometerReading,
    "fuel": FuelRecord,
    "work": WorkRecord,
    "expense": ExpenseRecord,
    "note": Note,
    "plan": Plan,
    "inspection": Inspection,
}


async def _record_in_household(
    kind: str, record_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> None:
    """Refuse a record belonging to another household (RNF-SEG-001).

    The household is never taken from the request: a vehicle is checked directly,
    everything else through the vehicle it hangs off.
    """
    if kind not in TAGGABLE_KINDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown record kind: {kind}"
        )
    model = _MODELS[kind]
    record = await db.get(model, record_id)
    if record is None or getattr(record, "deleted_at", None) is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    if kind == "vehicle":
        household_id = record.household_id
    else:
        vehicle = await db.get(Vehicle, record.vehicle_id)
        if vehicle is None or vehicle.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        household_id = vehicle.household_id
    if household_id != membership.household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")


@router.get("", response_model=list[TagUsage])
async def list_tags(membership: CurrentMembership, db: DbSession) -> list[TagUsage]:
    """Every tag in the household, with how many records carry it."""
    counts = (
        select(RecordTag.tag_id, func.count().label("uses")).group_by(RecordTag.tag_id).subquery()
    )
    rows = await db.execute(
        select(Tag, func.coalesce(counts.c.uses, 0))
        .outerjoin(counts, counts.c.tag_id == Tag.id)
        .where(Tag.household_id == membership.household_id)
        .order_by(Tag.name)
    )
    return [
        TagUsage(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            created_at=tag.created_at,
            record_count=uses,
        )
        for tag, uses in rows.all()
    ]


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> Tag:
    if membership.role not in _CAN_MANAGE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot manage tags")
    slug = tag_service.normalize(payload.name)
    existing = await db.scalar(
        select(Tag).where(Tag.household_id == membership.household_id, Tag.slug == slug)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"A tag named {existing.name} exists"
        )
    tag = Tag(
        household_id=membership.household_id,
        name=payload.name.strip(),
        slug=slug,
        color=payload.color,
        created_by=user.id,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def _tag_in_household(tag_id: uuid.UUID, membership: CurrentMembership, db: DbSession) -> Tag:
    tag = await db.get(Tag, tag_id)
    if tag is None or tag.household_id != membership.household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag


@router.patch("/{tag_id}", response_model=TagOut)
async def update_tag(
    tag_id: uuid.UUID, payload: TagUpdate, membership: CurrentMembership, db: DbSession
) -> Tag:
    if membership.role not in _CAN_MANAGE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot manage tags")
    tag = await _tag_in_household(tag_id, membership, db)
    if payload.name is not None:
        slug = tag_service.normalize(payload.name)
        clash = await db.scalar(
            select(Tag).where(
                Tag.household_id == membership.household_id, Tag.slug == slug, Tag.id != tag.id
            )
        )
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"A tag named {clash.name} exists"
            )
        tag.name = payload.name.strip()
        tag.slug = slug
    if payload.color is not None:
        tag.color = payload.color
    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: uuid.UUID, membership: CurrentMembership, db: DbSession) -> None:
    """Remove a tag, and with it every record's use of it.

    Deleting is immediate rather than recoverable: a tag carries no history of
    its own, and the records it was on are untouched apart from losing a label.
    """
    if membership.role not in _CAN_MANAGE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot manage tags")
    tag = await _tag_in_household(tag_id, membership, db)
    await db.delete(tag)
    await db.commit()


@router.get("/records/{kind}/{record_id}", response_model=list[TagOut])
async def list_record_tags(
    kind: str, record_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[Tag]:
    await _record_in_household(kind, record_id, membership, db)
    grouped = await tag_service.tags_for(kind, [record_id], db)
    return grouped.get(record_id, [])


@router.put("/records/{kind}/{record_id}", response_model=list[TagOut])
async def set_record_tags(
    kind: str,
    record_id: uuid.UUID,
    payload: RecordTagsIn,
    membership: CurrentMembership,
    db: DbSession,
) -> list[Tag]:
    """Replace the record's tags with the set the member submitted."""
    if membership.role not in _CAN_TAG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot edit records"
        )
    await _record_in_household(kind, record_id, membership, db)
    tags = await tag_service.set_tags(kind, record_id, payload.tag_ids, membership.household_id, db)
    await db.commit()
    return tags
