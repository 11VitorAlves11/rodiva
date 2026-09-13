import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Role


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str | None
    role: Role
    joined_at: datetime


class MemberRoleIn(BaseModel):
    role: Role


class InviteIn(BaseModel):
    role: Role
    email: EmailStr | None = None
    expires_in_hours: int = Field(default=72, ge=1, le=24 * 30)


class InviteOut(BaseModel):
    id: uuid.UUID
    role: Role
    email: str | None
    token: str
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvitePreviewOut(BaseModel):
    """What a bare token holder sees before signing in or registering."""

    household_name: str
    role: Role
