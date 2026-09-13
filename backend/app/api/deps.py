from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import read_session
from app.db.session import get_session
from app.models import Membership, User

DbSession = Annotated[AsyncSession, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_current_user(request: Request, db: DbSession, settings: AppSettings) -> User:
    """Resolve the session cookie to a user, or fail with 401.

    Every endpoint outside /auth depends on this: there is no data in Rodiva that
    is not owned by exactly one household, itself reached only through a member.
    """
    unauthorised = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise unauthorised
    user_id = read_session(token)
    if user_id is None:
        raise unauthorised
    user = await db.get(User, user_id)
    if user is None:
        raise unauthorised
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_membership(user: CurrentUser, db: DbSession) -> Membership:
    """The caller's membership in their (first, and for now only) household.

    Spec §2.1 allows a user to belong to more than one household but lets the
    first interface assume a single active one — this is that assumption, made
    explicit and in one place so switching households later is a matter of
    resolving it from the request instead of always taking the first row.
    """
    membership = await db.scalar(
        select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at)
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User belongs to no household"
        )
    return membership


CurrentMembership = Annotated[Membership, Depends(get_current_membership)]
