import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.models import Role, Webhook, WebhookDelivery
from app.schemas.webhooks import (
    WebhookCreated,
    WebhookDeliveryOut,
    WebhookIn,
    WebhookOut,
    WebhookUpdate,
)
from app.services import events

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# An endpoint receives the household's data, so managing one is an owner's job.
_CAN_MANAGE = {Role.OWNER}


def _require_owner(membership: CurrentMembership) -> None:
    if membership.role not in _CAN_MANAGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can manage webhooks"
        )


async def _get(hook_id: uuid.UUID, membership: CurrentMembership, db: DbSession) -> Webhook:
    hook = await db.get(Webhook, hook_id)
    if hook is None or hook.household_id != membership.household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return hook


@router.get("", response_model=list[WebhookOut])
async def list_webhooks(membership: CurrentMembership, db: DbSession) -> list[Webhook]:
    _require_owner(membership)
    rows = await db.scalars(
        select(Webhook)
        .where(Webhook.household_id == membership.household_id)
        .order_by(Webhook.created_at)
    )
    return list(rows)


@router.post("", response_model=WebhookCreated, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    payload: WebhookIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> WebhookCreated:
    """Register an endpoint. The signing secret is returned once, here."""
    _require_owner(membership)
    hook = Webhook(
        household_id=membership.household_id,
        description=payload.description,
        url=str(payload.url),
        secret=secrets.token_urlsafe(32),
        events=payload.events,
        created_by=user.id,
    )
    db.add(hook)
    await db.commit()
    await db.refresh(hook)
    return WebhookCreated(**WebhookOut.model_validate(hook).model_dump(), secret=hook.secret)


@router.patch("/{hook_id}", response_model=WebhookOut)
async def update_webhook(
    hook_id: uuid.UUID, payload: WebhookUpdate, membership: CurrentMembership, db: DbSession
) -> Webhook:
    _require_owner(membership)
    hook = await _get(hook_id, membership, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(hook, field, str(value) if field == "url" else value)
    await db.commit()
    await db.refresh(hook)
    return hook


@router.delete("/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(hook_id: uuid.UUID, membership: CurrentMembership, db: DbSession) -> None:
    _require_owner(membership)
    hook = await _get(hook_id, membership, db)
    await db.delete(hook)
    await db.commit()


@router.post("/{hook_id}/test", response_model=WebhookDeliveryOut)
async def send_test_event(
    hook_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> WebhookDelivery:
    """Queue a ping and try it straight away, so a new endpoint can be checked."""
    _require_owner(membership)
    hook = await _get(hook_id, membership, db)
    delivery = WebhookDelivery(
        webhook_id=hook.id,
        event="webhook.test",
        payload=events.envelope(
            household_id=membership.household_id,
            resource="webhook",
            action="test",
            entity_id=hook.id,
            vehicle_id=None,
            data={"message": "Rodiva test event"},
        ),
    )
    db.add(delivery)
    await db.commit()
    await events.flush(db)
    await db.commit()
    await db.refresh(delivery)
    return delivery


@router.get("/{hook_id}/deliveries", response_model=list[WebhookDeliveryOut])
async def list_deliveries(
    hook_id: uuid.UUID,
    membership: CurrentMembership,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[WebhookDelivery]:
    """The attempt log for one endpoint (RF-NOT-007)."""
    _require_owner(membership)
    await _get(hook_id, membership, db)
    rows = await db.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == hook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    return list(rows)


@router.post("/{hook_id}/deliveries/{delivery_id}/retry", response_model=WebhookDeliveryOut)
async def retry_delivery(
    hook_id: uuid.UUID,
    delivery_id: uuid.UUID,
    membership: CurrentMembership,
    db: DbSession,
) -> WebhookDelivery:
    """Put a given-up delivery back in the queue."""
    _require_owner(membership)
    await _get(hook_id, membership, db)
    delivery = await db.get(WebhookDelivery, delivery_id)
    if delivery is None or delivery.webhook_id != hook_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    delivery.status = "pending"
    delivery.attempts = 0
    delivery.next_attempt_at = datetime.now(UTC)
    await db.commit()
    await events.flush(db)
    await db.commit()
    await db.refresh(delivery)
    return delivery
