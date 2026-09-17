import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

#: The types a field can take (RF-ADM-007). "secret" is stored like any other
#: string but never sent back in full, so an API key parked in a custom field
#: does not leak through an ordinary read.
FIELD_TYPES: frozenset[str] = frozenset(
    {"text", "number", "currency", "date", "choice", "multi_choice", "checkbox", "url", "secret"}
)

#: Which record kinds can carry custom fields (RF-ADM-008, RF-VEI-014).
CUSTOM_FIELD_KINDS: frozenset[str] = frozenset(
    {"vehicle", "fuel", "work", "expense", "note", "plan", "inspection"}
)


class CustomFieldDefinition(Base):
    """A field the household added to a record kind (RF-ADM-007/008)."""

    __tablename__ = "custom_field_definitions"
    __table_args__ = (
        UniqueConstraint("household_id", "record_kind", "key", name="uq_custom_field_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    #: Stable identifier for the value map; the label can be renamed freely
    #: without orphaning everything already stored under it.
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Options for choice and multi_choice; empty for every other type.
    options: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Archived fields keep their stored values and stop appearing on forms,
    #: so retiring one never destroys what members already recorded.
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CustomFieldValue(Base):
    """One record's custom field values, as a single document.

    A row per field would multiply reads by the number of fields defined; the
    values are only ever read and written together, with the record itself.
    """

    __tablename__ = "custom_field_values"
    __table_args__ = (
        Index("ix_custom_field_values_record", "record_kind", "record_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    record_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
