"""add expense records

Revision ID: d9e20b341f52
Revises: cf18f72349a2
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
revision: str = "d9e20b341f52"
down_revision: str | None = "cf18f72349a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
def upgrade() -> None:
    op.create_table("expense_records", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("vehicle_id", sa.Uuid(), nullable=False), sa.Column("issued_on", sa.Date(), nullable=False), sa.Column("category", sa.String(50), nullable=False), sa.Column("amount", sa.Numeric(10, 2), nullable=False), sa.Column("supplier", sa.String(200)), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_by", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_expense_records_vehicle_id", "expense_records", ["vehicle_id"])
def downgrade() -> None:
    op.drop_index("ix_expense_records_vehicle_id", table_name="expense_records")
    op.drop_table("expense_records")
