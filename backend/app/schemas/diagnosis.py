"""Diagnosis intake and response schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class DiagnosisCreate(BaseModel):
    patient_id: str = Field(..., description="Target patient ID")
    diagnosis_name: str = Field(..., min_length=2, max_length=200)
    clinical_note: str = Field(..., min_length=5)
    medication: Optional[str] = None
    dosage: Optional[str] = None
    disclose_to_patient: bool = Field(
        default=True,
        description="Whether to disclose directly to patient or withhold/stage"
    )
    disclosure_reason: Optional[str] = Field(
        default=None,
        description="Required reason if disclosure is withheld (e.g. therapeutic privilege, compassionate non-disclosure)"
    )
    patient_facing_text: Optional[str] = Field(
        default=None,
        description="Plain-language patient translation"
    )

class DiagnosisOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    doctor_name: Optional[str] = None
    diagnosis_name: str
    clinical_note: str
    medication: Optional[str]
    dosage: Optional[str]
    disclose_to_patient: bool
    disclosure_reason: Optional[str]
    patient_facing_text: Optional[str]
    guardian_notified: bool
    created_at: datetime
    generated_flags: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
