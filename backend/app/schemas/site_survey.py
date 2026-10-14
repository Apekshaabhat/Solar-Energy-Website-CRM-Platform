from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


PROPERTY_TYPES = {"Residential", "Commercial", "Industrial"}
SURVEY_STATUSES = {"Scheduled", "In Progress", "Completed", "Cancelled"}


def validate_choice(value: Optional[str], allowed: set[str], field_name: str) -> Optional[str]:
    if value is None:
        return value
    cleaned = value.strip()
    if cleaned not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ValueError(f"{field_name} must be one of: {allowed_values}")
    return cleaned


class SiteSurveyBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=150)
    location: str = Field(..., min_length=2, max_length=150)
    property_type: str = Field(default="Residential")  # Residential, Commercial, Industrial
    survey_date: str = Field(..., min_length=3, max_length=50)  # "15 Sep 2026" or date string
    time_slot: str = Field(default="10:00 AM", max_length=50)
    assigned_to: str = Field(default="Rahul", max_length=100)
    status: str = Field(default="Scheduled")  # Scheduled, In Progress, Completed, Cancelled
    roof_information: Optional[str] = Field(default=None, max_length=2000)
    capacity_estimate: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("customer_name", "location", "survey_date", "time_slot", "assigned_to", mode="after")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned

    @field_validator("roof_information", "capacity_estimate", "notes", mode="after")
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
        return validate_choice(value, SURVEY_STATUSES, "status")


class SiteSurveyCreate(SiteSurveyBase):
    customer_id: Optional[int] = Field(default=None, ge=1)
    project_id: Optional[int] = Field(default=None, ge=1)
    lead_id: Optional[int] = Field(default=None, ge=1)
    assigned_user_id: Optional[int] = Field(default=None, ge=1)


class SiteSurveyCompleteRequest(BaseModel):
    roof_information: Optional[str] = Field(default=None, max_length=2000)
    capacity_estimate: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)



class SiteSurveyUpdate(BaseModel):
    customer_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    location: Optional[str] = Field(default=None, min_length=2, max_length=150)
    property_type: Optional[str] = None
    survey_date: Optional[str] = Field(default=None, min_length=3, max_length=50)
    time_slot: Optional[str] = Field(default=None, max_length=50)
    assigned_to: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = None
    customer_id: Optional[int] = Field(default=None, ge=1)
    project_id: Optional[int] = Field(default=None, ge=1)
    lead_id: Optional[int] = Field(default=None, ge=1)
    assigned_user_id: Optional[int] = Field(default=None, ge=1)
    roof_information: Optional[str] = Field(default=None, max_length=2000)
    capacity_estimate: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("customer_name", "location", "survey_date", "time_slot", "assigned_to", mode="after")
    @classmethod
    def strip_required_update_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank")
        return cleaned

    @field_validator("roof_information", "capacity_estimate", "notes", mode="after")
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
        return validate_choice(value, SURVEY_STATUSES, "status")


class SiteSurveyResponse(SiteSurveyBase):
    id: int
    customer_id: Optional[int] = None
    project_id: Optional[int] = None
    lead_id: Optional[int] = None
    assigned_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SiteSurveyListResponse(BaseModel):
    success: bool = True
    items: list[SiteSurveyResponse] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    limit: int = 10
    total_pages: int = 1
    tab_counts: Dict[str, int] = Field(default_factory=dict)
