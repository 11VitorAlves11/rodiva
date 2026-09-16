"""add fuel records

Revision ID: bd39d95e6c61
Revises: aa24d11b8e33
Create Date: 2026-09-13 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "bd39d95e6c61"
down_revision: str | None = "aa24d11b8e33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fuel_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("odometer_reading", sa.Integer(), nullable=True),
        sa.Column("volume_litres", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("fuel_type", sa.String(length=50), nullable=True),
        sa.Column("station", sa.String(length=200), nullable=True),
        sa.Column("full_tank", sa.Boolean(), nullable=False),
        sa.Column("excluded_from_consumption", sa.Boolean(), nullable=False),
        sa.Column("consumption_l_per_100km", sa.Numeric(precision=8, scale=3), nullable=True),
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
    op.create_index(op.f("ix_fuel_records_vehicle_id"), "fuel_records", ["vehicle_id"])
    op.create_index(op.f("ix_fuel_records_recorded_on"), "fuel_records", ["recorded_on"])


def downgrade() -> None:
    op.drop_index(op.f("ix_fuel_records_recorded_on"), table_name="fuel_records")
    op.drop_index(op.f("ix_fuel_records_vehicle_id"), table_name="fuel_records")
    op.drop_table("fuel_records")
