"""add saved views

Revision ID: 80a59d83f555
Revises: fb139c8990d4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "80a59d83f555"
down_revision: str | None = "fb139c8990d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_views",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("household_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("query", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_saved_views_household_id"), "saved_views", ["household_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_saved_views_household_id"), table_name="saved_views")
    op.drop_table("saved_views")
