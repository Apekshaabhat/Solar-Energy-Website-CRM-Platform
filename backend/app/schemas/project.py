from typing import Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


PROJECT_CATEGORIES = {"Residential", "Commercial", "Industrial"}
PROJECT_STATUSES = {"Planning", "In Progress", "Completed", "On Hold", "Cancelled"}


def validate_choice(value: Optional[str], allowed: set[str], field_name: str) -> Optional[str]:
    if value is None:
        return value
    cleaned = value.strip()
    if cleaned not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {allowed_values}")
    return cleaned


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., min_length=2, max_length=50)  # Residential, Commercial, Industrial
    location: str = Field(..., min_length=2, max_length=150)
    capacity: str = Field(..., min_length=1, max_length=50)  # e.g. "12 kW", "250 kW"
    capacity_kw: Optional[float] = Field(default=None, ge=0, le=100_000)
    status: str = Field(default="In Progress")  # Planning, In Progress, Completed, On Hold, Cancelled
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_public: bool = True
    estimated_cost: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    actual_cost: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    start_date: Optional[date] = None
    completion_date: Optional[date] = None

    @field_validator("name", "category", "location", "capacity", mode="after")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned

    @field_validator("image_url", mode="after")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("category", mode="after")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return validate_choice(value, PROJECT_CATEGORIES, "category")

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return validate_choice(value, PROJECT_STATUSES, "status")

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.completion_date and self.completion_date < self.start_date:
            raise ValueError("completion_date cannot be before start_date")
        return self


class ProjectCreate(ProjectBase):
    customer_id: Optional[int] = Field(default=None, ge=1)
    source_lead_id: Optional[int] = Field(default=None, ge=1)
    assigned_user_id: Optional[int] = Field(default=None, ge=1)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    category: Optional[str] = None
    location: Optional[str] = Field(default=None, min_length=2, max_length=150)
    capacity: Optional[str] = Field(default=None, min_length=1, max_length=50)
    capacity_kw: Optional[float] = Field(default=None, ge=0, le=100_000)
    status: Optional[str] = None
    customer_id: Optional[int] = Field(default=None, ge=1)
    source_lead_id: Optional[int] = Field(default=None, ge=1)
    assigned_user_id: Optional[int] = Field(default=None, ge=1)
    image_url: Optional[str] = Field(default=None, max_length=500)
    is_public: Optional[bool] = None
    estimated_cost: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    actual_cost: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    start_date: Optional[date] = None
    completion_date: Optional[date] = None

    @field_validator("name", "location", "capacity", mode="after")
    @classmethod
    def strip_required_update_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned

    @field_validator("image_url", mode="after")
    @classmethod
    def strip_optional_update_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("category", mode="after")
    @classmethod
    def validate_category(cls, value: Optional[str]) -> Optional[str]:
        return validate_choice(value, PROJECT_CATEGORIES, "category")

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        return validate_choice(value, PROJECT_STATUSES, "status")

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.completion_date and self.completion_date < self.start_date:
            raise ValueError("completion_date cannot be before start_date")
        return self


class ProjectResponse(ProjectBase):
    id: int
    customer_id: Optional[int] = None
    source_lead_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    customer_name: Optional[str] = None
    source_lead_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
