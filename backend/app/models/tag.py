import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

#: The record kinds a tag can be put on. The spec asks for tags on odometer
#: readings (RF-ODO-001), work (RF-INT-001), expenses (RF-DES-002), plans
#: (RF-PLA-003), inspections (RF-INS-006) and notes (§16); vehicles and fuel
#: join them so search and reports can filter the whole history by one tag.
TAGGABLE_KINDS: frozenset[str] = frozenset(
    {"vehicle", "odometer", "fuel", "work", "expense", "note", "plan", "inspection"}
)


class Tag(Base):
    """A reusable label owned by the household (RF-DOC-009, spec §2.1).

    Tags are shared across every vehicle, so the same "inverno" or "garantia"
    means one thing for the whole household rather than being retyped per record.
    """

    __tablename__ = "tags"
    __table_args__ = (
        # Two tags whose names differ only by case or accent would read as
        # duplicates in the picker, so uniqueness is on the normalised form.
        UniqueConstraint("household_id", "slug", name="uq_tags_household_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    #: Lower-cased and unaccented `name`, for uniqueness and for matching a
    #: search term typed without accents.
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    #: Hex colour chosen by the member (RF-DOC-009).
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6B7280")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RecordTag(Base):
    """Which tag sits on which record.

    One table for every kind rather than a join table per record type: the kinds
    are already addressed polymorphically in search and the bin, and eight join
    tables would each need their own migration, query and cleanup path.

    There is deliberately no foreign key to the record: it could not point at
    eight tables at once. Deletion is soft everywhere these kinds live, so a
    restored record keeps its tags; purging one clears its rows here.
    """

    __tablename__ = "record_tags"
    __table_args__ = (
        Index("ix_record_tags_record", "record_kind", "record_id"),
        UniqueConstraint("tag_id", "record_kind", "record_id", name="uq_record_tags_unique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
