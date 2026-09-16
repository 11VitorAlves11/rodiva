"""Recording the household's audit trail (RNF-SEG-009).

Events are added to the caller's session rather than committed here, so the
trail lands in the same transaction as the change it describes: an action that
is rolled back leaves no event, and an event never describes a change that did
not happen.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent, Membership, User

# Actions worth a trail entry. Grouped by the noun they act on so the listing
# can be filtered by prefix.
MEMBER_ROLE_CHANGED = "member.role_changed"
MEMBER_REMOVED = "member.removed"
INVITE_CREATED = "invite.created"
INVITE_REVOKED = "invite.revoked"
API_KEY_CREATED = "api_key.created"
API_KEY_REVOKED = "api_key.revoked"
RECORD_DELETED = "record.deleted"
RECORD_RESTORED = "record.restored"
RECORD_PURGED = "record.purged"
VEHICLE_DELETED = "vehicle.deleted"
VEHICLE_RESTORED = "vehicle.restored"
EXPORT_CREATED = "export.created"


def actor_label(user: User | None) -> str:
    """How the actor should read in the trail once the account may be gone."""
    if user is None:
        return ""
    return user.name or user.email


def record(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    summary: str = "",
    context: dict[str, Any] | None = None,
) -> AuditEvent:
    """Add an audit event to the current transaction. The caller commits."""
    event = AuditEvent(
        household_id=household_id,
        actor_user_id=actor.id if actor else None,
        actor_label=actor_label(actor),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary[:300],
        context=context,
    )
    db.add(event)
    return event


def record_record_action(
    db: AsyncSession,
    *,
    membership: Membership,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    vehicle_id: uuid.UUID | None = None,
    summary: str = "",
) -> AuditEvent:
    """Shorthand for the delete/restore/purge of one vehicle record."""
    return record(
        db,
        household_id=membership.household_id,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        context={"vehicle_id": str(vehicle_id)} if vehicle_id else None,
    )
