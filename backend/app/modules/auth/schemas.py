from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int | None
    full_name: str
    email: EmailStr
    role: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=32)


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "residente"


class InvitationCreated(BaseModel):
    id: int
    email: EmailStr
    expires_at: str


class InvitationAccept(BaseModel):
    token: str = Field(min_length=32)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    phone: str | None = Field(default=None, max_length=30)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=32)
    new_password: str = Field(min_length=10, max_length=128)


class MessageOut(BaseModel):
    message: str
