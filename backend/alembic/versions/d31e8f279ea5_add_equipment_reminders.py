"""add equipment reminders

Revision ID: d31e8f279ea5
Revises: b77001e38774
Create Date: 2026-09-14 13:15:26.655838
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d31e8f279ea5"
down_revision: str | None = "b77001e38774"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reminders", sa.Column("equipment_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_reminders_equipment_id"), "reminders", ["equipment_id"], unique=False)
    op.create_foreign_key(
        "reminders_equipment_id_fkey",
        "reminders",
        "equipment",
        ["equipment_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("reminders_equipment_id_fkey", "reminders", type_="foreignkey")
    op.drop_index(op.f("ix_reminders_equipment_id"), table_name="reminders")
    op.drop_column("reminders", "equipment_id")
