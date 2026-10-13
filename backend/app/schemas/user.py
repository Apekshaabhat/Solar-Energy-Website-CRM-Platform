from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.validators import AppEmailStr


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: AppEmailStr
    phone: Optional[str] = None
    role: str = Field(default="Sales Rep")  # Admin, Manager, Sales Rep, Support, Customer
    status: str = Field(default="Active")  # Active, Invited, Inactive


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[AppEmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    id: int
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
