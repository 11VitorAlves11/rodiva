import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

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

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    household_id: uuid.UUID
    household_name: str
    role: Role


class MeOut(BaseModel):
    user: UserOut
    membership: MembershipOut
