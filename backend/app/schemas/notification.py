from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    updated_at: datetime
    time: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int
