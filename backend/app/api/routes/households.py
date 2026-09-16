"""Household membership management (spec §2): list, invite, change role, remove.

Invites are accepted through /auth (register with a token, or an already
signed-in user accepting one) since that is where a caller may not yet hold a
session.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.models import Invite, Membership, Role, User
from app.schemas.households import InviteIn, InviteOut, MemberOut, MemberRoleIn
from app.services import audit

router = APIRouter(prefix="/household", tags=["household"])
_CAN_MANAGE_MEMBERS = {Role.OWNER, Role.MANAGER}


def _require_manager(role: Role) -> None:
    if role not in _CAN_MANAGE_MEMBERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot manage members"
        )


async def _count_owners(household_id: uuid.UUID, db: DbSession) -> int:
    result = await db.scalars(
        select(Membership).where(
            Membership.household_id == household_id, Membership.role == Role.OWNER
        )
    )
    return len(list(result))


async def _get_member(household_id: uuid.UUID, user_id: uuid.UUID, db: DbSession) -> Membership:
    target = await db.scalar(
        select(Membership).where(
            Membership.household_id == household_id, Membership.user_id == user_id
        )
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return target


@router.get("/members", response_model=list[MemberOut])
async def list_members(membership: CurrentMembership, db: DbSession) -> list[MemberOut]:
    rows = await db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.household_id == membership.household_id)
        .order_by(Membership.created_at)
    )
    return [
        MemberOut(
            user_id=user.id,
            email=user.email,
            name=user.name,
            role=member.role,
            joined_at=member.created_at,
        )
        for member, user in rows.all()
    ]


@router.patch("/members/{user_id}", response_model=MemberOut)
async def update_member_role(
    user_id: uuid.UUID,
    payload: MemberRoleIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> MemberOut:
    _require_manager(membership.role)
    target = await _get_member(membership.household_id, user_id, db)
    previous_role = target.role
    if target.role == Role.OWNER and membership.role != Role.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can change an owner's role"
        )
    if payload.role == Role.OWNER and membership.role != Role.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can grant ownership"
        )
    if (
        target.role == Role.OWNER
        and payload.role != Role.OWNER
        and await _count_owners(membership.household_id, db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A household needs at least one owner"
        )
    target.role = payload.role
    member_user = await db.get(User, user_id)
    assert member_user is not None
    member_label = member_user.name or member_user.email
    audit.record(
        db,
        household_id=membership.household_id,
        actor=user,
        action=audit.MEMBER_ROLE_CHANGED,
        entity_type="membership",
        entity_id=user_id,
        summary=f"{member_label}: {previous_role.value} → {payload.role.value}",
        context={"from": previous_role.value, "to": payload.role.value},
    )
    await db.commit()
    return MemberOut(
        user_id=member_user.id,
        email=member_user.email,
        name=member_user.name,
        role=target.role,
        joined_at=target.created_at,
    )


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: uuid.UUID, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> None:
    _require_manager(membership.role)
    target = await _get_member(membership.household_id, user_id, db)
    if target.role == Role.OWNER and membership.role != Role.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can remove an owner"
        )
    if target.role == Role.OWNER and await _count_owners(membership.household_id, db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A household needs at least one owner"
        )
    removed = await db.get(User, user_id)
    audit.record(
        db,
        household_id=membership.household_id,
        actor=user,
        action=audit.MEMBER_REMOVED,
        entity_type="membership",
        entity_id=user_id,
        summary=removed.name or removed.email if removed else str(user_id),
        context={"role": target.role.value},
    )
    await db.delete(target)
    await db.commit()


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(membership: CurrentMembership, db: DbSession) -> list[Invite]:
    _require_manager(membership.role)
    result = await db.scalars(
        select(Invite)
        .where(Invite.household_id == membership.household_id)
        .order_by(Invite.created_at.desc())
    )
    return list(result)


@router.post("/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def create_invite(
    payload: InviteIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> Invite:
    _require_manager(membership.role)
    if payload.role == Role.OWNER and membership.role != Role.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can invite an owner"
        )
    invite = Invite(
        household_id=membership.household_id,
        token=secrets.token_urlsafe(32),
        role=payload.role.value,
        email=payload.email,
        created_by=user.id,
        expires_at=datetime.now(UTC) + timedelta(hours=payload.expires_in_hours),
    )
    db.add(invite)
    audit.record(
        db,
        household_id=membership.household_id,
        actor=user,
        action=audit.INVITE_CREATED,
        entity_type="invite",
        entity_id=invite.id,
        summary=f"{payload.email or 'any address'} as {payload.role.value}",
        context={"role": payload.role.value, "email": payload.email},
    )
    await db.commit()
    await db.refresh(invite)
    return invite


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: uuid.UUID, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> None:
    _require_manager(membership.role)
    invite = await db.get(Invite, invite_id)
    if invite is None or invite.household_id != membership.household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    invite.revoked_at = datetime.now(UTC)
    audit.record(
        db,
        household_id=membership.household_id,
        actor=user,
        action=audit.INVITE_REVOKED,
        entity_type="invite",
        entity_id=invite.id,
        summary=invite.email or "any address",
    )
    await db.commit()
