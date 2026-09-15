"""Clinical reconciliation flag schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class FlagOut(BaseModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    diagnosis_id: str
    diagnosis_name: Optional[str] = None
    historical_reference: str
    root_cause: str  # doctor_gap, patient_gap, no_fault, intentional
    severity: str    # LOW, MEDIUM, HIGH
    status: str      # OPEN, UNDER_REVIEW, RESOLVED, DISMISSED
    explanation: str
    resolution_note: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

class FlagResolveRequest(BaseModel):
    resolution_note: str = Field(..., min_length=5, description="Clinical action taken or reconciliation note")

class FlagDismissRequest(BaseModel):
    dismissal_reason: str = Field(..., min_length=5, description="Clinical justification for dismissing this flag")

class FlagSummaryStats(BaseModel):
    total_active: int
    high_priority: int
    medium_priority: int
    low_priority: int
    under_review: int
    resolved_today: int
