from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ActivityResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    title: str
    description: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    user_id: Optional[int] = None
    status: Optional[str] = None
    created_at: datetime
    time_ago: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
