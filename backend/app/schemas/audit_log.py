"""Audit log schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AuditLogOut(BaseModel):
    id: str
    actor_id: str
    actor_role: str
    action: str
    target_type: str
    target_id: str
    details: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True
