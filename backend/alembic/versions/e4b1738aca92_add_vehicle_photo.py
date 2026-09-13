"""add vehicle photo

Revision ID: e4b1738aca92
Revises: d9e20b341f52
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
revision: str = "e4b1738aca92"
down_revision: str | None = "d9e20b341f52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
def upgrade() -> None:
    op.add_column("vehicles", sa.Column("photo_url", sa.String(500), nullable=True))
def downgrade() -> None:
    op.drop_column("vehicles", "photo_url")
