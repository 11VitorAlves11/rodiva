"""add calendar feeds

Revision ID: a4d8e7c2b190
Revises: c8a1f4b6e2d7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4d8e7c2b190"
down_revision: str | None = "c8a1f4b6e2d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calendar_feeds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_calendar_feeds_household_id"), "calendar_feeds", ["household_id"], unique=False
    )
    op.create_index(
        op.f("ix_calendar_feeds_token_hash"), "calendar_feeds", ["token_hash"], unique=True
    )
    op.create_index(op.f("ix_calendar_feeds_user_id"), "calendar_feeds", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_calendar_feeds_user_id"), table_name="calendar_feeds")
    op.drop_index(op.f("ix_calendar_feeds_token_hash"), table_name="calendar_feeds")
    op.drop_index(op.f("ix_calendar_feeds_household_id"), table_name="calendar_feeds")
    op.drop_table("calendar_feeds")
