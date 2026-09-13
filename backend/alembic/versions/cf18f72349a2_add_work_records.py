"""add work records

Revision ID: cf18f72349a2
Revises: bd39d95e6c61
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "cf18f72349a2"
down_revision: str | None = "bd39d95e6c61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("work_records", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("vehicle_id", sa.Uuid(), nullable=False), sa.Column("recorded_on", sa.Date(), nullable=False), sa.Column("kind", sa.String(length=20), nullable=False), sa.Column("description", sa.String(length=500), nullable=False), sa.Column("odometer_reading", sa.Integer(), nullable=True), sa.Column("total_cost", sa.Numeric(precision=10, scale=2), nullable=True), sa.Column("supplier", sa.String(length=200), nullable=True), sa.Column("notes", sa.String(length=2000), nullable=True), sa.Column("created_by", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_work_records_vehicle_id"), "work_records", ["vehicle_id"])
    op.create_index(op.f("ix_work_records_recorded_on"), "work_records", ["recorded_on"])


def downgrade() -> None:
    op.drop_index(op.f("ix_work_records_recorded_on"), table_name="work_records")
    op.drop_index(op.f("ix_work_records_vehicle_id"), table_name="work_records")
    op.drop_table("work_records")
