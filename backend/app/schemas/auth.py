import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Role


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10)
    name: str | None = None
    # RF-AGR-001: the household is created together with the first account.
    household_name: str = Field(min_length=1, max_length=200)


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
