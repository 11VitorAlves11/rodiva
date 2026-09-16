import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.models import ApiKey, Role

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class KeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scope: Literal["read", "write"] = "read"
    vehicle_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    expires_in_days: int = Field(default=90, ge=1, le=365)


class KeyOut(BaseModel):
    id: uuid.UUID
    name: str
    scope: str
    vehicle_ids: list[str]
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class CreatedKey(KeyOut):
    token: str


@router.get("", response_model=list[KeyOut])
async def list_keys(
    user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> list[ApiKey]:
    return list(
        await db.scalars(
            select(ApiKey)
            .where(ApiKey.user_id == user.id, ApiKey.household_id == membership.household_id)
            .order_by(ApiKey.created_at.desc())
        )
    )


@router.post("", response_model=CreatedKey, status_code=201)
async def create_key(
    payload: KeyIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> CreatedKey:
    if payload.scope == "write" and membership.role == Role.READER:
        raise HTTPException(status_code=403, detail="Readers can only create read-only keys")
    for vehicle_id in payload.vehicle_ids:
        await _vehicle_in_household(vehicle_id, membership, db)
    token = "rdv_" + secrets.token_urlsafe(32)
    key = ApiKey(
        user_id=user.id,
        household_id=membership.household_id,
        name=payload.name,
        scope=payload.scope,
        vehicle_ids=sorted(set(map(str, payload.vehicle_ids))),
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=payload.expires_in_days),
    )
    db.add(key)
    await db.commit()
    return CreatedKey(**KeyOut.model_validate(key).model_dump(), token=token)


@router.delete("/{key_id}", status_code=204)
async def revoke_key(
    key_id: uuid.UUID, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> None:
    key = await db.get(ApiKey, key_id)
    if key is None or key.user_id != user.id or key.household_id != membership.household_id:
        raise HTTPException(status_code=404, detail="API key not found")
    key.revoked_at = datetime.now(UTC)
    await db.commit()
