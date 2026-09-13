"""Local authentication (RF-AUT-001): email + password, session cookie.

OIDC is deferred to the parity phase (RF-AUT-006); AUTH_MODE is fixed to "local"
for now (app.core.config.Settings), so there is nothing to branch on here yet.
"""

import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentMembership, CurrentUser, DbSession
from app.core.config import Settings
from app.core.security import (
    PasswordTooLongError,
    hash_password,
    issue_session,
    verify_password,
)
from app.models import Household, Membership, Role, User
from app.schemas.auth import LoginIn, MembershipOut, MeOut, RegisterIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Hashing a throwaway password on unknown emails keeps the response time of a wrong
# email and a wrong password comparable, so login cannot be used to enumerate users.
_DUMMY_HASH = hash_password("not-a-real-password-but-long-enough")


def _set_session_cookie(response: Response, user_id: uuid.UUID, settings: Settings) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        issue_session(user_id),
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookies_secure,
        path="/",
    )


@router.post("/register", response_model=MeOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterIn, response: Response, db: DbSession, settings: AppSettings
) -> MeOut:
    if not settings.allow_public_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration is closed")

    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    try:
        password_hash = hash_password(payload.password)
    except PasswordTooLongError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # RF-AGR-001: the first account creates its household in the same step.
    household = Household(
        name=payload.household_name,
        locale=settings.default_locale,
        currency=settings.default_currency,
        distance_unit=settings.default_distance_unit,
        timezone=settings.default_timezone,
    )
    user = User(email=payload.email, password_hash=password_hash, name=payload.name)
    db.add_all([household, user])
    await db.flush()

    membership = Membership(user_id=user.id, household_id=household.id, role=Role.OWNER)
    db.add(membership)
    await db.commit()

    _set_session_cookie(response, user.id, settings)
    return MeOut(
        user=UserOut.model_validate(user),
        membership=MembershipOut(
            household_id=household.id, household_name=household.name, role=membership.role
        ),
    )


@router.post("/login", response_model=MeOut)
async def login(
    payload: LoginIn, response: Response, db: DbSession, settings: AppSettings
) -> MeOut:
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        raise invalid
    if not verify_password(payload.password, user.password_hash):
        raise invalid

    membership = await db.scalar(
        select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at)
    )
    if membership is None:
        raise invalid
    household = await db.get(Household, membership.household_id)
    assert household is not None

    _set_session_cookie(response, user.id, settings)
    return MeOut(
        user=UserOut.model_validate(user),
        membership=MembershipOut(
            household_id=household.id, household_name=household.name, role=membership.role
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: AppSettings) -> None:
    # RF-AUT-003 (all sessions) needs a revocation store; this ends the caller's
    # own signed cookie, which is what a stateless session can do without one.
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser, membership: CurrentMembership, db: DbSession) -> MeOut:
    household = await db.get(Household, membership.household_id)
    assert household is not None
    return MeOut(
        user=UserOut.model_validate(user),
        membership=MembershipOut(
            household_id=household.id, household_name=household.name, role=membership.role
        ),
    )
