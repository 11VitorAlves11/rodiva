import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class SoftDelete:
    """Recoverable deletion for the records that make up a vehicle's history.

    Spec §23.2 keeps `deleted_at` and `deleted_by` on a deleted record rather
    than removing the row, so it can be restored and so the trail still has
    something to point at. Every read of these tables has to exclude the
    deleted ones — see `app.db.filters.active`.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
