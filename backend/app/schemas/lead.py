from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.schemas.validators import AppEmailStr


PROPERTY_TYPES = {"Residential", "Commercial", "Industrial"}
LEAD_SOURCES = {
    "Website",
    "Calculator",
    "Referral",
    "Cold Call",
    "Ad Campaign",
    "Social Media",
    "Direct Enquiry",
    "Google Ads",
}
LEAD_STATUSES = {"New", "Contacted", "Site Survey", "Quoted", "Converted", "Cancelled", "Lost"}



def validate_choice(value: Optional[str], allowed: set[str], field_name: str) -> Optional[str]:
    if value is None:
        return value
    cleaned = value.strip()
    if cleaned not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {allowed_values}")
    return cleaned


class LeadBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    contact: str = Field(..., min_length=3, max_length=100)
    email: Optional[AppEmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    location: str = Field(..., min_length=2, max_length=150)
    property_type: str = Field(default="Residential")
    source: str = Field(default="Website")
    status: str = Field(default="New")  # New, Contacted, Site Survey, Quoted, Converted, Lost
    notes: Optional[str] = Field(default=None, max_length=2000)
    estimated_value: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)

    @field_validator("name", "contact", "location", mode="after")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned

    @field_validator("phone", "notes", mode="after")
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

    @field_validator("source", mode="after")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return validate_choice(value, LEAD_SOURCES, "source")

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return validate_choice(value, LEAD_STATUSES, "status")


class LeadCreate(LeadBase):
    assigned_user_id: Optional[int] = Field(default=None, ge=1)
    customer_id: Optional[int] = Field(default=None, ge=1)


class LeadUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    contact: Optional[str] = Field(default=None, min_length=3, max_length=100)
    email: Optional[AppEmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, min_length=2, max_length=150)
    property_type: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=2000)
    estimated_value: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    assigned_user_id: Optional[int] = Field(default=None, ge=1)
    customer_id: Optional[int] = Field(default=None, ge=1)

    @field_validator("name", "contact", "location", mode="after")
    @classmethod
    def strip_required_update_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned

    @field_validator("phone", "notes", mode="after")
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

    @field_validator("source", mode="after")
    @classmethod
    def validate_source(cls, value: Optional[str]) -> Optional[str]:
        return validate_choice(value, LEAD_SOURCES, "source")

    @field_validator("status", mode="after")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        return validate_choice(value, LEAD_STATUSES, "status")


class LeadScheduleSurveyRequest(BaseModel):
    survey_date: str = Field(..., min_length=3, max_length=50)
    time_slot: str = Field(default="10:00 AM", max_length=50)
    assigned_to: str = Field(default="Rahul", max_length=100)
    roof_information: Optional[str] = Field(default=None, max_length=2000)
    capacity_estimate: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)


class LeadConvertRequest(BaseModel):
    project_name: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = None
    capacity: Optional[str] = Field(default=None, max_length=50)
    capacity_kw: Optional[float] = Field(default=None, ge=0, le=100_000)
    estimated_cost: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    actual_cost: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    is_public: Optional[bool] = True


class LeadResponse(LeadBase):
    id: int
    assigned_user_id: Optional[int] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    surveys_count: Optional[int] = 0
    projects_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime
    # Helper formatted date for frontend matching
    date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    success: bool = True
    items: list[LeadResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 10
    total_pages: int = 1
    tab_counts: Dict[str, int] = Field(default_factory=dict)
