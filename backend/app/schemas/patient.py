"""Patient and access control schemas."""
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field

class PatientBase(BaseModel):
    age: int
    gender: str
    conditions: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    guardian_id: Optional[str] = None

class PatientOut(PatientBase):
    id: str
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PatientTimelineItem(BaseModel):
    date: datetime
    type: str  # ALLERGY, CONDITION, MEDICATION, DIAGNOSIS, FLAG, CORRECTION
    title: str
    description: str
    severity: Optional[str] = None
    metadata: Optional[dict] = None

class PatientHistoryOut(BaseModel):
    patient: PatientOut
    timeline: List[PatientTimelineItem]
    has_full_access: bool

class AccessRequestCreate(BaseModel):
    patient_id: str
    notes: Optional[str] = "Clinical consultation access request"

class AccessRequestRespond(BaseModel):
    approve: bool  # True -> APPROVED, False -> DENIED

class AccessRequestOut(BaseModel):
    id: str
    doctor_id: str
    doctor_name: Optional[str] = None
    doctor_specialty: Optional[str] = None
    patient_id: str
    patient_name: Optional[str] = None
    status: str
    notes: Optional[str]
    requested_at: datetime
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True
