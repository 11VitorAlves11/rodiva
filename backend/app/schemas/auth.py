import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import Role


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)
    name: str | None = None
    # RF-AGR-001: the household is created together with the first account,
    # unless an invite (RF-AGR-002) already places the new user in one.
    household_name: str | None = Field(default=None, min_length=1, max_length=200)
    invite_token: str | None = None

    @model_validator(mode="after")
    def household_name_or_invite(self) -> "RegisterIn":
        if not self.household_name and not self.invite_token:
            raise ValueError("A household name or an invite token is required")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    locale: str
    timezone: str

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    household_id: uuid.UUID
    household_name: str
    role: Role


class MeOut(BaseModel):
    user: UserOut
    membership: MembershipOut


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    locale: Literal["pt-PT", "en"] = "pt-PT"
    timezone: str = Field(default="Europe/Lisbon", max_length=50)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Unknown timezone") from exc
        return value


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=72)


class SessionOut(BaseModel):
    id: uuid.UUID
    user_agent: str
    created_at: datetime
    expires_at: datetime
    current: bool


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=32, max_length=200)
    password: str = Field(min_length=10, max_length=72)
