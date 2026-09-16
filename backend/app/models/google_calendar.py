import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GoogleCalendarConnection(Base):
    """One member's link to their own Google Calendar (RF-GCAL-001/002).

    A distinct feature from `CalendarFeed` (the read-only ICS subscription):
    this one writes events into a Google calendar the member picked.
    """

    __tablename__ = "google_calendar_connections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    google_account_email: Mapped[str] = mapped_column(String(320), nullable=False)
    # Null until the member finishes the setup wizard and picks a calendar.
    calendar_id: Mapped[str | None] = mapped_column(String(500))
    # Which vehicles' reminders to sync — empty/absent means none selected yet.
    synced_vehicle_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    access_token_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_setup")
    last_error: Mapped[str | None] = mapped_column(String(2_000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CalendarSyncEvent(Base):
    """Bookkeeping for one reminder synced into one connection's calendar (RF-GCAL-009)."""

    __tablename__ = "calendar_sync_events"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "reminder_id", name="uq_calendar_sync_event_connection_reminder"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("google_calendar_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reminder_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_event_id: Mapped[str | None] = mapped_column(String(500))
    external_calendar_id: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="synced")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(2_000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
