"""Electric vehicle charging records."""

import sqlalchemy as sa
from alembic import op

revision = "b23d005ef093"
down_revision = "a12c004def92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "charging_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "vehicle_id",
            sa.Uuid(),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("odometer_reading", sa.Integer()),
        sa.Column("energy_kwh", sa.Numeric(10, 3), nullable=False),
        sa.Column("total_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 3), nullable=False),
        sa.Column("soc_start", sa.Integer()),
        sa.Column("soc_end", sa.Integer()),
        sa.Column("location", sa.String(200)),
        sa.Column("charger_type", sa.String(100), nullable=False),
        sa.Column("notes", sa.String(2000)),
        sa.Column("efficiency_kwh_per_100km", sa.Numeric(10, 3)),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_charging_records_vehicle_id", "charging_records", ["vehicle_id"])


def downgrade() -> None:
    op.drop_table("charging_records")
