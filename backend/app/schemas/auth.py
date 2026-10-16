from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.validators import AppEmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    email: AppEmailStr
    password: str = Field(..., min_length=1)
    remember_me: Optional[bool] = False


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: AppEmailStr
    password: str = Field(..., min_length=6, max_length=128)
    phone: Optional[str] = None
    role: Optional[str] = "Customer"


class ActivateAccountRequest(BaseModel):
    token: str = Field(..., min_length=16, description="Invitation or activation token")
    password: str = Field(..., min_length=6, max_length=128)
    confirm_password: str = Field(..., min_length=6, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: AppEmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)
    confirm_password: str = Field(..., min_length=6, max_length=128)


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[AppEmailStr] = None
    phone: Optional[str] = None
