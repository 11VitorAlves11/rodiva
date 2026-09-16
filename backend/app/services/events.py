"""Household events and their delivery to webhooks (RF-NOT-006/007, RF-API-008).

An event is queued in the same transaction as the change that produced it, so a
rolled-back change emits nothing and a receiver that is unreachable holds
nothing up. Sending happens later, from the scheduled run.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)

EVENT_VERSION = 1
SIGNATURE_HEADER = "X-Rodiva-Signature"
# Attempt n waits 2^n minutes, so roughly a minute, two, four ... up to about
# half an hour before the delivery is given up on.
MAX_ATTEMPTS = 6
TIMEOUT_SECONDS = 10

# The events this build emits. Names are "<resource>.<action>" (spec §24.2).
AUDIT_EVENTS = {
    "record.deleted": "record.deleted",
    "record.restored": "record.restored",
    "record.purged": "record.deleted",
    "vehicle.deleted": "vehicle.deleted",
    "vehicle.restored": "vehicle.restored",
    "member.role_changed": "member.role_changed",
    "member.removed": "member.removed",
    "invite.created": "member.invited",
}


def envelope(
    *,
    household_id: uuid.UUID,
    resource: str,
    action: str,
    entity_id: uuid.UUID | None,
    vehicle_id: uuid.UUID | None,
    data: dict[str, Any] | None,
) -> dict[str, Any]:
    """The event body, carrying everything RF-API-008 asks for."""
    return {
        "version": EVENT_VERSION,
        "id": str(uuid.uuid4()),
        "occurred_at": datetime.now(UTC).isoformat(),
        "household_id": str(household_id),
        "vehicle_id": str(vehicle_id) if vehicle_id else None,
        "resource": resource,
        "action": action,
        "entity_id": str(entity_id) if entity_id else None,
        "data": data or {},
    }


async def emit(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    resource: str,
    action: str,
    entity_id: uuid.UUID | None = None,
    vehicle_id: uuid.UUID | None = None,
    data: dict[str, Any] | None = None,
) -> int:
    """Queue one event for every endpoint that wants it. The caller commits."""
    event = f"{resource}.{action}"
    hooks = list(
        await db.scalars(
            select(Webhook).where(Webhook.household_id == household_id, Webhook.active.is_(True))
        )
    )
    body = envelope(
        household_id=household_id,
        resource=resource,
        action=action,
        entity_id=entity_id,
        vehicle_id=vehicle_id,
        data=data,
    )
    queued = 0
    for hook in hooks:
        if hook.events and event not in hook.events:
            continue
        db.add(WebhookDelivery(webhook_id=hook.id, event=event, payload=body))
        queued += 1
    return queued


def sign(secret: str, body: bytes) -> str:
    """The signature a receiver should recompute to trust the body (RF-NOT-007)."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def _attempt(delivery: WebhookDelivery, hook: Webhook, client: httpx.AsyncClient) -> None:
    body = json.dumps(delivery.payload, separators=(",", ":"), sort_keys=True).encode()
    delivery.attempts += 1
    try:
        response = await client.post(
            hook.url,
            content=body,
            headers={
                "Content-Type": "application/json",
                SIGNATURE_HEADER: sign(hook.secret, body),
                "X-Rodiva-Event": delivery.event,
                "X-Rodiva-Delivery": str(delivery.id),
                "X-Rodiva-Timestamp": str(int(datetime.now(UTC).timestamp())),
            },
            timeout=TIMEOUT_SECONDS,
        )
        delivery.response_status = response.status_code
        if 200 <= response.status_code < 300:
            delivery.status = "sent"
            delivery.delivered_at = datetime.now(UTC)
            delivery.last_error = ""
            hook.last_success_at = delivery.delivered_at
            hook.last_error = ""
            return
        raise httpx.HTTPStatusError("rejected", request=response.request, response=response)
    except Exception as error:  # noqa: BLE001 - every failure is recorded, never raised
        delivery.last_error = f"{type(error).__name__}: {error}"[:300]
        hook.last_error = delivery.last_error
        if delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = "failed"
        else:
            delivery.next_attempt_at = datetime.now(UTC) + timedelta(minutes=2**delivery.attempts)


async def flush(db: AsyncSession, limit: int = 50) -> tuple[int, int]:
    """Send what is due. Returns (delivered, failed). Never raises."""
    now = datetime.now(UTC)
    rows = list(
        await db.scalars(
            select(WebhookDelivery)
            .where(WebhookDelivery.status == "pending", WebhookDelivery.next_attempt_at <= now)
            .order_by(WebhookDelivery.created_at)
            .limit(limit)
        )
    )
    if not rows:
        return 0, 0
    delivered = failed = 0
    async with httpx.AsyncClient() as client:
        for delivery in rows:
            hook = await db.get(Webhook, delivery.webhook_id)
            if hook is None or not hook.active:
                delivery.status = "failed"
                delivery.last_error = "endpoint is gone or switched off"
                failed += 1
                continue
            await _attempt(delivery, hook, client)
            if delivery.status == "sent":
                delivered += 1
            else:
                failed += 1
    return delivered, failed
