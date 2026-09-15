"""Patient history correction schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class CorrectionCreate(BaseModel):
    patient_id: Optional[str] = None  # Inferred if caller is patient
    entity_type: str = Field(..., description="MEDICATION, CONDITION, ALLERGY, or NOTE")
    current_value: str = Field(..., min_length=2)
    suggested_value: str = Field(..., min_length=2)
    note: str = Field(..., min_length=5, description="E.g. 'I stopped this medication in March'")

class CorrectionDismissRequest(BaseModel):
    dismissal_reason: str = Field(..., min_length=5)

class CorrectionOut(BaseModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    doctor_id: Optional[str] = None
    entity_type: str
    current_value: str
    suggested_value: str
    note: str
    status: str  # PENDING, ACCEPTED, DISMISSED
    dismissal_reason: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]

    class Config:
        from_attributes = True
