from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import read_session
from app.db.session import get_session
from app.models import AuthSession, Membership, User

DbSession = Annotated[AsyncSession, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_current_session(
    request: Request, db: DbSession, settings: AppSettings
) -> AuthSession:
    unauthorised = HTTPException(status_code=401, detail="Not authenticated")
    token = request.cookies.get(settings.session_cookie_name)
    session_id = read_session(token) if token else None
    session = await db.get(AuthSession, session_id) if session_id else None
    if session is None or session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
        raise unauthorised
    return session


CurrentSession = Annotated[AuthSession, Depends(get_current_session)]


async def get_current_user(request: Request, db: DbSession, settings: AppSettings) -> User:
    if request.headers.get("authorization"):
        from app.services.api_keys import resolve_api_key

        key = await resolve_api_key(request, db)
        user_id = key.user_id
    else:
        session = await get_current_session(request, db, settings)
        user_id = session.user_id
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_membership(
    user: CurrentUser, request: Request, db: DbSession, settings: AppSettings
) -> Membership:
    key = getattr(request.state, "api_key", None)
    query = select(Membership).where(Membership.user_id == user.id)
    if key is not None:
        query = query.where(Membership.household_id == key.household_id)
    else:
        session = await get_current_session(request, db, settings)
    if key is None and session.household_id is not None:
        query = query.where(Membership.household_id == session.household_id)
    membership = await db.scalar(query.order_by(Membership.created_at))
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User belongs to no household"
        )
    return membership


CurrentMembership = Annotated[Membership, Depends(get_current_membership)]
