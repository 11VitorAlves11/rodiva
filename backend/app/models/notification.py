import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotificationPreference(Base):
    """What one member wants to hear about, and through which channel (RF-NOT-003)."""

    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "household_id", name="uq_notification_pref_member"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_inapp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    channel_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Web Push (RF-NOT-002). Off until the member turns it on from a browser
    #: that has granted permission — RF-PWA-012 forbids asking unprompted.
    channel_push: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Notify at this urgency or anything more pressing.
    min_urgency: Mapped[str] = mapped_column(String(20), nullable=False, default="urgent")
    # Empty means every vehicle in the household.
    vehicle_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # Local hours, inclusive start and exclusive end; null disables the window.
    quiet_hours_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quiet_hours_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Notification(Base):
    """One thing worth telling a member about.

    `dedup_key` is unique per member (RF-NOT-004): the evaluator can run as
    often as it likes without repeating itself. The key carries the urgency, so
    a reminder that becomes more pressing produces a new notification while the
    same state does not (RF-NOT-005).
    """

    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "dedup_key", name="uq_notification_dedup"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    # Data, not wording: the client phrases it in the reader's own language.
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    context: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationDelivery(Base):
    """One attempt to get a notification to a member down one channel.

    Kept so a failed send is visible rather than silent (RF-NOT-004), and so a
    channel that was skipped during quiet hours can be picked up later.
    """

    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
