"""add plans

Revision ID: 9b3c2d1e0f4a
Revises: f41b003abc91
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9b3c2d1e0f4a"
down_revision: str | None = "f41b003abc91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(length=20), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("due_odometer", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("completed_work_record_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["completed_work_record_id"], ["work_records.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("completed_work_record_id"),
    )
    op.create_index(op.f("ix_plans_due_date"), "plans", ["due_date"], unique=False)
    op.create_index(op.f("ix_plans_vehicle_id"), "plans", ["vehicle_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plans_vehicle_id"), table_name="plans")
    op.drop_index(op.f("ix_plans_due_date"), table_name="plans")
    op.drop_table("plans")
