"""add notes

Revision ID: a522ef3e8671
Revises: f241cbea19d4
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "a522ef3e8671"
down_revision: str | None = "f241cbea19d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_vehicle_id", "notes", ["vehicle_id"])


def downgrade() -> None:
    op.drop_index("ix_notes_vehicle_id", table_name="notes")
    op.drop_table("notes")
