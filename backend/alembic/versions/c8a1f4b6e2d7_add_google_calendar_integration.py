"""add google calendar integration

Revision ID: c8a1f4b6e2d7
Revises: b7e1f5a9032c
Create Date: 2026-09-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8a1f4b6e2d7"
down_revision: str | None = "b7e1f5a9032c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "google_calendar_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("google_account_email", sa.String(length=320), nullable=False),
        sa.Column("calendar_id", sa.String(length=500), nullable=True),
        sa.Column("synced_vehicle_ids", sa.JSON(), nullable=False),
        sa.Column("access_token_encrypted", sa.String(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.String(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_google_calendar_connections_household_id"),
        "google_calendar_connections",
        ["household_id"],
        unique=False,
    )

    op.create_table(
        "calendar_sync_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("reminder_id", sa.Uuid(), nullable=False),
        sa.Column("external_event_id", sa.String(length=500), nullable=True),
        sa.Column("external_calendar_id", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["google_calendar_connections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reminder_id"], ["reminders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id", "reminder_id", name="uq_calendar_sync_event_connection_reminder"
        ),
    )
    op.create_index(
        op.f("ix_calendar_sync_events_connection_id"),
        "calendar_sync_events",
        ["connection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calendar_sync_events_reminder_id"),
        "calendar_sync_events",
        ["reminder_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_calendar_sync_events_reminder_id"), table_name="calendar_sync_events")
    op.drop_index(op.f("ix_calendar_sync_events_connection_id"), table_name="calendar_sync_events")
    op.drop_table("calendar_sync_events")
    op.drop_index(
        op.f("ix_google_calendar_connections_household_id"),
        table_name="google_calendar_connections",
    )
    op.drop_table("google_calendar_connections")
