from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.validators import AppEmailStr


PROPERTY_TYPES = {"Residential", "Commercial", "Industrial"}
CUSTOMER_STATUSES = {"Active", "Inactive"}


def validate_choice(value: Optional[str], allowed: set[str], field_name: str) -> Optional[str]:
    if value is None:
        return value
    cleaned = value.strip()
    if cleaned not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {allowed_values}")
    return cleaned


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    contact: str = Field(..., min_length=3, max_length=100)
    email: Optional[AppEmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    location: str = Field(..., min_length=2, max_length=150)
    property_type: str = Field(default="Residential")  # Residential, Commercial, Industrial
    status: str = Field(default="Active")  # Active, Inactive
    customer_since: Optional[str] = Field(default=None, max_length=30)

    @field_validator("name", "contact", "location", mode="after")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned

    @field_validator("phone", "customer_since", mode="after")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("property_type", mode="after")
    @classmethod
    def validate_property_type(cls, value: str) -> str:
        return validate_choice(value, PROPERTY_TYPES, "property_type")

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return validate_choice(value, CUSTOMER_STATUSES, "status")


class CustomerCreate(CustomerBase):
    assigned_user_id: Optional[int] = Field(default=None, ge=1)


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    contact: Optional[str] = Field(default=None, min_length=3, max_length=100)
    email: Optional[AppEmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, min_length=2, max_length=150)
    property_type: Optional[str] = None
    status: Optional[str] = None
    customer_since: Optional[str] = Field(default=None, max_length=30)
    assigned_user_id: Optional[int] = Field(default=None, ge=1)

    @field_validator("name", "contact", "location", mode="after")
    @classmethod
    def strip_required_update_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned

    @field_validator("phone", "customer_since", mode="after")
    @classmethod
    def strip_optional_update_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("property_type", mode="after")
    @classmethod
    def validate_property_type(cls, value: Optional[str]) -> Optional[str]:
        return validate_choice(value, PROPERTY_TYPES, "property_type")

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        return validate_choice(value, CUSTOMER_STATUSES, "status")


class CustomerResponse(CustomerBase):
    id: int
    assigned_user_id: Optional[int] = None
    total_projects: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerOverviewResponse(CustomerResponse):
    leads: list[dict] = []
    site_surveys: list[dict] = []
    projects: list[dict] = []
    activities: list[dict] = []
