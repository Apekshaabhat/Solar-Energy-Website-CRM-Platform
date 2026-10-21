from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, StrictBool, field_validator

from app.schemas.validators import AppEmailStr


class SystemSettingsUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=200)
    support_email: Optional[AppEmailStr] = None
    email_notifications: Optional[StrictBool] = None
    sms_notifications: Optional[StrictBool] = None
    lead_alerts: Optional[StrictBool] = None
    two_factor_auth: Optional[StrictBool] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("company_name", mode="before")
    @classmethod
    def strip_company_name(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) else value


class SystemSettingsResponse(BaseModel):
    id: int
    company_name: str
    support_email: str
    email_notifications: bool
    sms_notifications: bool
    lead_alerts: bool
    two_factor_auth: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
