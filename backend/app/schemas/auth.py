from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.validators import AppEmailStr, StrongPasswordStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    jti: Optional[str] = None
    ver: Optional[int] = None


class LoginRequest(BaseModel):
    email: AppEmailStr
    password: str = Field(..., min_length=1)
    remember_me: Optional[bool] = False


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: AppEmailStr
    password: StrongPasswordStr
    phone: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class ActivateAccountRequest(BaseModel):
    token: str = Field(..., min_length=16, description="Invitation or activation token")
    password: str = Field(..., min_length=6, max_length=128)
    confirm_password: Optional[str] = Field(None, min_length=6, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: AppEmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Reset token received via email/console")
    new_password: StrongPasswordStr


class ActivateRequest(BaseModel):
    token: str = Field(..., min_length=1, description="Activation token received via invitation")
    password: StrongPasswordStr


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: StrongPasswordStr
    confirm_password: str = Field(..., min_length=1)


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[AppEmailStr] = None
    phone: Optional[str] = None

