"""Reading, attaching and detaching tags across the record kinds (RF-DOC-009)."""

import re
import unicodedata
import uuid
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RecordTag, Tag

#: Everything a member types is compared in this form, so "Inverno", "inverno"
#: and "invérno" are one tag rather than three near-identical ones in the picker.
_COMBINING = dict.fromkeys(range(0x300, 0x370))

_HEX_COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize(value: str) -> str:
    """Lower-case and strip accents, for uniqueness and accent-blind search."""
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return unicodedata.normalize("NFC", decomposed.translate(_COMBINING))


def is_valid_colour(value: str) -> bool:
    return bool(_HEX_COLOUR.match(value))


async def tags_for(
    kind: str, record_ids: list[uuid.UUID], db: AsyncSession
) -> dict[uuid.UUID, list[Tag]]:
    """The tags on each of these records, in one query rather than one per record."""
    if not record_ids:
        return {}
    rows = await db.execute(
        select(RecordTag.record_id, Tag)
        .join(Tag, Tag.id == RecordTag.tag_id)
        .where(RecordTag.record_kind == kind, RecordTag.record_id.in_(record_ids))
        .order_by(Tag.name)
    )
    grouped: dict[uuid.UUID, list[Tag]] = defaultdict(list)
    for record_id, tag in rows.all():
        grouped[record_id].append(tag)
    return grouped


async def set_tags(
    kind: str,
    record_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
    household_id: uuid.UUID,
    db: AsyncSession,
) -> list[Tag]:
    """Make the record's tags exactly `tag_ids`, ignoring ids from another household.

    Replacing rather than merging is what a form submission means: the member
    sees the full set of tags and sends back the set they want.
    """
    tags: list[Tag] = []
    if tag_ids:
        wanted = await db.execute(
            select(Tag).where(Tag.id.in_(tag_ids), Tag.household_id == household_id)
        )
        tags = list(wanted.scalars().all())
    await db.execute(
        delete(RecordTag).where(RecordTag.record_kind == kind, RecordTag.record_id == record_id)
    )
    for tag in tags:
        db.add(RecordTag(tag_id=tag.id, record_kind=kind, record_id=record_id))
    return sorted(tags, key=lambda tag: tag.name)


async def clear_tags(kind: str, record_id: uuid.UUID, db: AsyncSession) -> None:
    """Drop a purged record's tag rows; nothing points at them any more."""
    await db.execute(
        delete(RecordTag).where(RecordTag.record_kind == kind, RecordTag.record_id == record_id)
    )
