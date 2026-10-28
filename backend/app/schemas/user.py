from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.validators import AppEmailStr, StrongPasswordStr

ALLOWED_ROLES = ["Admin", "Sales Rep"]
ALLOWED_STATUSES = ["Active", "Invited", "Inactive"]


def normalize_role(v: str) -> str:
    cleaned = v.strip().lower().replace("_", " ")
    if cleaned == "admin":
        return "Admin"
    if cleaned in ("sales rep", "sales representative"):
        return "Sales Rep"
    raise ValueError(f"Invalid role '{v}'. Allowed roles: {', '.join(ALLOWED_ROLES)}")


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: AppEmailStr
    phone: Optional[str] = None
    role: str = Field(default="Sales Rep")
    status: str = Field(default="Active")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        return normalize_role(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        for allowed in ALLOWED_STATUSES:
            if v.strip().lower() == allowed.lower():
                return allowed
        raise ValueError(f"Invalid status '{v}'. Allowed statuses: {', '.join(ALLOWED_STATUSES)}")


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: AppEmailStr
    phone: Optional[str] = None
    role: str = Field(default="Sales Rep")
    status: Optional[str] = Field(default="Invited")
    password: Optional[StrongPasswordStr] = None
    customer_id: Optional[int] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        return normalize_role(v)


class UserInviteRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: AppEmailStr
    role: str = Field(default="Sales Rep")
    phone: Optional[str] = None
    customer_id: Optional[int] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        return normalize_role(v)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[AppEmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    customer_id: Optional[int] = None
    password: Optional[StrongPasswordStr] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_role(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        for allowed in ALLOWED_STATUSES:
            if v.strip().lower() == allowed.lower():
                return allowed
        raise ValueError(f"Invalid status '{v}'. Allowed statuses: {', '.join(ALLOWED_STATUSES)}")


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    status: str
    customer_id: Optional[int] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserStatsResponse(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    invited_users: int
    users_by_role: Dict[str, int]
    totalUsers: Optional[int] = None
    activeUsers: Optional[int] = None
    inactiveUsers: Optional[int] = None
    invitedUsers: Optional[int] = None
    usersByRole: Optional[Dict[str, int]] = None

    def model_post_init(self, __context: Any) -> None:
        self.totalUsers = self.total_users
        self.activeUsers = self.active_users
        self.inactiveUsers = self.inactive_users
        self.invitedUsers = self.invited_users
        self.usersByRole = self.users_by_role
