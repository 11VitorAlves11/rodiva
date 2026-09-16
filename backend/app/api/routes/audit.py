import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, DbSession
from app.models import AuditEvent, Role
from app.schemas.audit import AuditPage

router = APIRouter(prefix="/audit", tags=["audit"])

# The trail names who did what to whom, so it stays with the profiles that
# already administer the household (spec §2.3).
_CAN_READ = {Role.OWNER, Role.MANAGER}


@router.get("", response_model=AuditPage)
async def list_audit_events(
    membership: CurrentMembership,
    db: DbSession,
    action: str | None = None,
    entity_id: uuid.UUID | None = None,
    before: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> AuditPage:
    if membership.role not in _CAN_READ:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot read the audit trail"
        )
    query = select(AuditEvent).where(AuditEvent.household_id == membership.household_id)
    if action:
        # A bare noun ("record") matches every action on it; a full action matches itself.
        clause = (
            AuditEvent.action == action
            if "." in action
            else AuditEvent.action.startswith(f"{action}.")
        )
        query = query.where(clause)
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    if before:
        query = query.where(AuditEvent.created_at < before)
    # One extra row tells us whether another page exists without a second count query.
    rows = list(await db.scalars(query.order_by(AuditEvent.created_at.desc()).limit(limit + 1)))
    has_more = len(rows) > limit
    items = rows[:limit]
    return AuditPage(
        items=items,  # type: ignore[arg-type]
        next_before=items[-1].created_at if has_more and items else None,
    )
