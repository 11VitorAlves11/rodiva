"""What the instance is doing right now (RF-ADM-009).

Read-only, and restricted to the owner: it names the configured integrations and
how much disk the uploads take, which is not everyone's business.
"""

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select, text

from app.api.deps import AppSettings, CurrentMembership, DbSession
from app.models import Attachment, Notification, Role, Vehicle, Webhook
from app.schemas.admin import InstanceStatus, StorageUsage, TaskStatus
from app.services import scheduler

router = APIRouter(prefix="/admin", tags=["admin"])

#: The page exposes configuration and disk figures, so it stays with the owner.
_CAN_READ = {Role.OWNER}


def _directory_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


@router.get("/status", response_model=InstanceStatus)
async def instance_status(
    membership: CurrentMembership, db: DbSession, settings: AppSettings
) -> InstanceStatus:
    if membership.role not in _CAN_READ:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can read this"
        )

    database_reachable = True
    database_version = ""
    migration: str | None = None
    try:
        database_version = str(await db.scalar(text("SHOW server_version")) or "")
        migration = await db.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception:
        # The page's whole job is to say when something is wrong, so a failure
        # here is a finding to report rather than an error to raise.
        database_reachable = False

    storage_path = Path(settings.storage_path)
    usage = StorageUsage(path=str(storage_path), exists=storage_path.is_dir())
    if usage.exists:
        try:
            usage.used_bytes = _directory_bytes(storage_path)
            usage.free_bytes = shutil.disk_usage(storage_path).free
        except OSError:
            usage.readable = False

    counts: dict[str, int] = {}
    for label, column in (
        ("vehicles", Vehicle.id),
        ("attachments", Attachment.id),
        ("notifications", Notification.id),
        ("webhooks", Webhook.id),
    ):
        counts[label] = await db.scalar(select(func.count(column))) or 0

    return InstanceStatus(
        app_name=settings.app_name,
        version="0.2.0",
        environment=settings.environment,
        auth_mode=settings.auth_mode,
        public_registration=settings.allow_public_registration,
        database_reachable=database_reachable,
        database_version=database_version,
        migration_revision=migration,
        storage=usage,
        tasks=TaskStatus(
            notifications_interval_seconds=settings.notification_interval_seconds,
            notifications_running=scheduler.is_running(),
        ),
        integrations=_integrations(settings),
        counts=counts,
    )


def _integrations(settings: Any) -> dict[str, bool]:
    """Which optional pieces an operator has actually configured."""
    return {
        "smtp": bool(settings.smtp_host and settings.smtp_from),
        "google_calendar": settings.google_calendar_enabled,
        "oidc": settings.oidc_enabled,
        "web_push": settings.web_push_enabled,
    }
