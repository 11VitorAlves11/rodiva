"""Local authentication, revocable sessions and household selection."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from sqlalchemy import delete, select, update

from app.api.deps import AppSettings, CurrentMembership, CurrentSession, CurrentUser, DbSession
from app.core.config import Settings
from app.core.security import (
    PasswordTooLongError,
    hash_password,
    issue_session,
    verify_password,
)
from app.models import AuthSession, Household, Invite, Membership, PasswordReset, Role, User
from app.schemas.auth import (
    ForgotPasswordIn,
    LoginIn,
    MembershipOut,
    MeOut,
    PasswordIn,
    ProfileIn,
    RegisterIn,
    ResetPasswordIn,
    SessionOut,
    UserOut,
)
from app.schemas.households import InvitePreviewOut
from app.services.account_recovery import send_password_reset, throttle

router = APIRouter(prefix="/auth", tags=["auth"])

# Hashing a throwaway password on unknown emails keeps the response time of a wrong
# email and a wrong password comparable, so login cannot be used to enumerate users.
_DUMMY_HASH = hash_password("not-a-real-password-but-long-enough")


async def _valid_invite(token: str, db: DbSession) -> Invite:
    invite = await db.scalar(select(Invite).where(Invite.token == token).with_for_update())
    if (
        invite is None
        or invite.revoked_at is not None
        or invite.accepted_at is not None
        or invite.expires_at < datetime.now(UTC)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found or expired"
        )
    return invite


async def _set_session_cookie(
    response: Response,
    user_id: uuid.UUID,
    household_id: uuid.UUID,
    settings: Settings,
    request: Request,
    db: DbSession,
) -> None:
    session = AuthSession(
        user_id=user_id,
        household_id=household_id,
        user_agent=request.headers.get("user-agent", "")[:500],
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.session_max_age),
    )
    db.add(session)
    await db.commit()
    response.set_cookie(
        settings.session_cookie_name,
        issue_session(session.id),
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookies_secure,
        path="/",
    )


def _check_invite_email(invite: Invite, email: str) -> None:
    if invite.email and invite.email.casefold() != email.casefold():
        raise HTTPException(status_code=403, detail="Invite is for a different email address")


@router.post("/register", response_model=MeOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterIn, response: Response, request: Request, db: DbSession, settings: AppSettings
) -> MeOut:
    if not settings.allow_public_registration and not payload.invite_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration is closed")

    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    try:
        password_hash = hash_password(payload.password)
    except PasswordTooLongError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    invite = await _valid_invite(payload.invite_token, db) if payload.invite_token else None

    if invite is not None:
        _check_invite_email(invite, str(payload.email))

    user = User(email=payload.email, password_hash=password_hash, name=payload.name)
    db.add(user)

    if invite is not None:
        # RF-AGR-002: an accepted invite places the new account straight into
        # the inviting household, instead of creating one of its own.
        household = await db.get(Household, invite.household_id)
        assert household is not None
        await db.flush()
        membership = Membership(user_id=user.id, household_id=household.id, role=Role(invite.role))
        invite.accepted_at = datetime.now(UTC)
        db.add(membership)
    else:
        # RF-AGR-001: the first account creates its household in the same step.
        household = Household(
            name=payload.household_name,
            locale=settings.default_locale,
            currency=settings.default_currency,
            distance_unit=settings.default_distance_unit,
            timezone=settings.default_timezone,
        )
        db.add(household)
        await db.flush()
        membership = Membership(user_id=user.id, household_id=household.id, role=Role.OWNER)
        db.add(membership)

    await db.commit()

    await _set_session_cookie(response, user.id, household.id, settings, request, db)
    return MeOut(
        user=UserOut.model_validate(user),
        membership=MembershipOut(
            household_id=household.id, household_name=household.name, role=membership.role
        ),
    )


@router.post("/login", response_model=MeOut)
async def login(
    payload: LoginIn, response: Response, request: Request, db: DbSession, settings: AppSettings
) -> MeOut:
    await throttle(request, str(payload.email), "login", db)
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

    await _set_session_cookie(response, user.id, household.id, settings, request, db)
    return MeOut(
        user=UserOut.model_validate(user),
        membership=MembershipOut(
            household_id=household.id, household_name=household.name, role=membership.role
        ),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response, settings: AppSettings, session: CurrentSession, db: DbSession
) -> None:
    session.revoked_at = datetime.now(UTC)
    await db.commit()
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


@router.get("/invites/{token}", response_model=InvitePreviewOut)
async def preview_invite(token: str, db: DbSession) -> InvitePreviewOut:
    invite = await _valid_invite(token, db)
    household = await db.get(Household, invite.household_id)
    assert household is not None
    return InvitePreviewOut(household_name=household.name, role=Role(invite.role))


@router.post("/invites/{token}/accept", response_model=MeOut)
async def accept_invite(
    token: str, user: CurrentUser, session: CurrentSession, db: DbSession
) -> MeOut:
    invite = await _valid_invite(token, db)
    _check_invite_email(invite, user.email)
    existing = await db.scalar(
        select(Membership).where(
            Membership.user_id == user.id, Membership.household_id == invite.household_id
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Already a member of this household"
        )
    membership = Membership(
        user_id=user.id, household_id=invite.household_id, role=Role(invite.role)
    )
    invite.accepted_at = datetime.now(UTC)
    db.add(membership)
    session.household_id = invite.household_id
    await db.commit()
    household = await db.get(Household, invite.household_id)
    assert household is not None
    return MeOut(
        user=UserOut.model_validate(user),
        membership=MembershipOut(
            household_id=household.id, household_name=household.name, role=membership.role
        ),
    )


@router.patch("/profile", response_model=UserOut)
async def update_profile(payload: ProfileIn, user: CurrentUser, db: DbSession) -> User:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.commit()
    return user


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    user: CurrentUser, session: CurrentSession, db: DbSession
) -> list[SessionOut]:
    rows = await db.scalars(
        select(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        )
        .order_by(AuthSession.created_at.desc())
    )
    return [
        SessionOut(
            id=row.id,
            user_agent=row.user_agent,
            created_at=row.created_at,
            expires_at=row.expires_at,
            current=row.id == session.id,
        )
        for row in rows
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: uuid.UUID,
    user: CurrentUser,
    session: CurrentSession,
    response: Response,
    settings: AppSettings,
    db: DbSession,
) -> None:
    target = await db.get(AuthSession, session_id)
    if target is None or target.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    target.revoked_at = datetime.now(UTC)
    await db.commit()
    if target.id == session.id:
        response.delete_cookie(settings.session_cookie_name, path="/")


@router.post("/logout-all", status_code=204)
async def logout_all(
    user: CurrentUser,
    response: Response,
    settings: AppSettings,
    db: DbSession,
) -> None:
    await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id)
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.post("/password", status_code=204)
async def change_password(
    payload: PasswordIn,
    user: CurrentUser,
    session: CurrentSession,
    db: DbSession,
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    try:
        user.password_hash = hash_password(payload.new_password)
    except PasswordTooLongError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.id != session.id,
        )
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()


@router.get("/households", response_model=list[MembershipOut])
async def list_households(user: CurrentUser, db: DbSession) -> list[MembershipOut]:
    rows = await db.execute(
        select(Membership, Household)
        .join(Household, Household.id == Membership.household_id)
        .where(Membership.user_id == user.id)
        .order_by(Household.name)
    )
    return [
        MembershipOut(household_id=house.id, household_name=house.name, role=member.role)
        for member, house in rows
    ]


@router.post("/households/{household_id}/activate", response_model=MeOut)
async def activate_household(
    household_id: uuid.UUID,
    user: CurrentUser,
    session: CurrentSession,
    db: DbSession,
) -> MeOut:
    membership = await db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.household_id == household_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Household not found")
    session.household_id = household_id
    await db.commit()
    return await me(user, membership, db)


@router.get("/options")
async def auth_options(settings: AppSettings) -> dict[str, bool]:
    return {
        "registration": settings.allow_public_registration,
        "password_recovery": bool(settings.smtp_host and settings.smtp_from),
    }


@router.post("/forgot-password", status_code=202)
async def forgot_password(
    payload: ForgotPasswordIn,
    request: Request,
    tasks: BackgroundTasks,
    settings: AppSettings,
    db: DbSession,
) -> dict[str, str]:
    await throttle(request, str(payload.email), "recovery", db)
    if not settings.smtp_host or not settings.smtp_from:
        raise HTTPException(status_code=503, detail="Password recovery is not configured")
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is not None:
        token = secrets.token_urlsafe(32)
        await db.execute(delete(PasswordReset).where(PasswordReset.expires_at < datetime.now(UTC)))
        db.add(
            PasswordReset(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                user_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )
        await db.commit()
        tasks.add_task(send_password_reset, settings, user.email, token, user.locale)
    return {"message": "If an account exists, password recovery instructions will be sent."}


@router.post("/reset-password", status_code=204)
async def reset_password(payload: ResetPasswordIn, request: Request, db: DbSession) -> None:
    await throttle(request, hashlib.sha256(payload.token.encode()).hexdigest(), "reset", db)
    now = datetime.now(UTC)
    # Lock the user before the token so concurrent tokens for the same user
    # cannot both reset the password or deadlock when invalidating one another.
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    user_id = await db.scalar(
        select(PasswordReset.user_id).where(PasswordReset.token_hash == token_hash)
    )
    user = (
        await db.scalar(select(User).where(User.id == user_id).with_for_update())
        if user_id
        else None
    )
    reset = await db.get(PasswordReset, token_hash)
    if user is None or reset is None or reset.used_at is not None or reset.expires_at <= now:
        raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
    try:
        user.password_hash = hash_password(payload.password)
    except PasswordTooLongError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.execute(
        update(PasswordReset).where(PasswordReset.user_id == user.id).values(used_at=now)
    )
    await db.execute(
        update(AuthSession).where(AuthSession.user_id == user.id).values(revoked_at=now)
    )
    await db.commit()
