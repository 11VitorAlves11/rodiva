"""add reminders

Revision ID: f241cbea19d4
Revises: e4b1738aca92
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
revision: str = "f241cbea19d4"
down_revision: str | None = "e4b1738aca92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
def upgrade() -> None:
    op.create_table("reminders", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("vehicle_id", sa.Uuid(), nullable=False), sa.Column("title", sa.String(300), nullable=False), sa.Column("due_date", sa.Date()), sa.Column("due_odometer", sa.Integer()), sa.Column("repeat_days", sa.Integer()), sa.Column("repeat_distance", sa.Integer()), sa.Column("notes", sa.String(2000)), sa.Column("status", sa.String(20), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("created_by", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_reminders_vehicle_id", "reminders", ["vehicle_id"])
def downgrade() -> None:
    op.drop_index("ix_reminders_vehicle_id", table_name="reminders")
    op.drop_table("reminders")
