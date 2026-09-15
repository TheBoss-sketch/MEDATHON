"""Pydantic schemas for user authentication and authorization."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=150, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(..., description="Role must be PATIENT, DOCTOR, or GUARDIAN")
    
    # Optional role-specific metadata
    age: Optional[int] = None
    gender: Optional[str] = None
    specialty: Optional[str] = None
    hospital: Optional[str] = None
    qualifications: Optional[str] = None
    linked_patient_id: Optional[str] = None
    relationship: Optional[str] = None

class UserLogin(BaseModel):
    email: str = Field(..., min_length=5, max_length=150)
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
