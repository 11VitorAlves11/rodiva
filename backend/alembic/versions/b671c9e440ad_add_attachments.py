"""add attachments

Revision ID: b671c9e440ad
Revises: a522ef3e8671
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
revision: str = "b671c9e440ad"
down_revision: str | None = "a522ef3e8671"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
def upgrade() -> None:
    op.create_table("attachments", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("vehicle_id", sa.Uuid(), nullable=False), sa.Column("filename", sa.String(300), nullable=False), sa.Column("content_type", sa.String(100), nullable=False), sa.Column("size", sa.Integer(), nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("storage_key", sa.String(500), nullable=False), sa.Column("created_by", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["created_by"], ["users.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("storage_key"))
    op.create_index("ix_attachments_vehicle_id", "attachments", ["vehicle_id"])
def downgrade() -> None:
    op.drop_index("ix_attachments_vehicle_id", table_name="attachments")
    op.drop_table("attachments")
