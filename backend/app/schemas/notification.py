"""Notification schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    related_id: Optional[str] = None
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True
