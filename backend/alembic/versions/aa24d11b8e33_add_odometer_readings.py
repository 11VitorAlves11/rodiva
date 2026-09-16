"""add odometer readings

Revision ID: aa24d11b8e33
Revises: c4997eb00071
Create Date: 2026-09-13 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "aa24d11b8e33"
down_revision: str | None = "c4997eb00071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "odometer_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("reading", sa.Integer(), nullable=False),
        sa.Column("start_reading", sa.Integer(), nullable=True),
        sa.Column("distance", sa.Integer(), nullable=True),
        sa.Column("is_adjustment", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_odometer_readings_vehicle_id"), "odometer_readings", ["vehicle_id"])
    op.create_index(op.f("ix_odometer_readings_recorded_on"), "odometer_readings", ["recorded_on"])


def downgrade() -> None:
    op.drop_index(op.f("ix_odometer_readings_recorded_on"), table_name="odometer_readings")
    op.drop_index(op.f("ix_odometer_readings_vehicle_id"), table_name="odometer_readings")
    op.drop_table("odometer_readings")
