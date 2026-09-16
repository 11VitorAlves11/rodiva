import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey, Membership, Role

# Account management and security settings always require an interactive session.
_ALLOWED_RESOURCES = {
    "vehicles",
    "reports",
    "search",
    "imports",
    "inventory",
    "equipment",
    "inspection-templates",
}


async def resolve_api_key(request: Request, db: AsyncSession) -> ApiKey:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.startswith("rdv_"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    key = await db.scalar(
        select(ApiKey).where(ApiKey.token_hash == hashlib.sha256(token.encode()).hexdigest())
    )
    if key is None or key.revoked_at is not None or key.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Invalid API key")
    membership = await db.scalar(
        select(Membership).where(
            Membership.user_id == key.user_id, Membership.household_id == key.household_id
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=403, detail="API key owner no longer belongs to this household"
        )
    parts = request.url.path.strip("/").split("/")
    if parts[:2] == ["api", "v1"]:
        parts = parts[2:]
    elif parts[:1] == ["api"]:
        parts = parts[1:]
    else:
        raise HTTPException(status_code=403, detail="API keys cannot access this resource")
    if not parts or parts[0] not in _ALLOWED_RESOURCES:
        raise HTTPException(status_code=403, detail="API keys cannot access this resource")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and (
        key.scope != "write" or membership.role == Role.READER
    ):
        raise HTTPException(status_code=403, detail="API key is read-only")
    if key.vehicle_ids:
        # Global search/reports/imports could expose or write multiple vehicles;
        # restricted keys only access explicitly scoped vehicle endpoints.
        if len(parts) < 2 or parts[0] != "vehicles":
            raise HTTPException(
                status_code=403, detail="Use a vehicle-specific endpoint with this key"
            )
        try:
            vehicle_id = str(uuid.UUID(parts[1]))
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="Vehicle is outside the key scope") from exc
        if vehicle_id not in key.vehicle_ids:
            raise HTTPException(status_code=403, detail="Vehicle is outside the key scope")
    request.state.api_key = key
    return key
