"""Registering a browser for Web Push (RF-NOT-002, RF-PWA-012)."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import delete, select

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.models import PushSubscription
from app.schemas.push import PushKey, PushSubscriptionIn, PushSubscriptionOut

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/key", response_model=PushKey)
async def public_key(settings: AppSettings) -> PushKey:
    """The VAPID public key the browser needs before it can subscribe.

    `enabled` is what the UI goes by: without it the app would ask for
    permission it could never act on, and a refused prompt does not come back.
    """
    return PushKey(enabled=settings.web_push_enabled, public_key=settings.vapid_public_key)


@router.get("", response_model=list[PushSubscriptionOut])
async def list_subscriptions(user: CurrentUser, db: DbSession) -> list[PushSubscription]:
    rows = await db.scalars(
        select(PushSubscription)
        .where(PushSubscription.user_id == user.id)
        .order_by(PushSubscription.created_at.desc())
    )
    return list(rows)


@router.post("", response_model=PushSubscriptionOut, status_code=status.HTTP_201_CREATED)
async def subscribe(
    payload: PushSubscriptionIn,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
) -> PushSubscription:
    if not settings.web_push_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This instance has no VAPID keys configured",
        )
    # A browser re-subscribes with the same endpoint after a permission change
    # or an update, so the endpoint is the identity rather than a new row.
    existing = await db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == payload.endpoint)
    )
    if existing is not None:
        existing.user_id = user.id
        existing.p256dh = payload.p256dh
        existing.auth = payload.auth
        existing.last_used_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(existing)
        return existing

    subscription = PushSubscription(
        user_id=user.id,
        endpoint=payload.endpoint,
        p256dh=payload.p256dh,
        auth=payload.auth,
        user_agent=request.headers.get("user-agent", "")[:300] or None,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(payload: PushSubscriptionIn, user: CurrentUser, db: DbSession) -> None:
    """Forget this browser. Scoped to the caller, so one member cannot mute another."""
    await db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == payload.endpoint,
            PushSubscription.user_id == user.id,
        )
    )
    await db.commit()
