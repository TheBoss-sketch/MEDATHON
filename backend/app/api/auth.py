"""Authentication and authorization endpoints."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.guardian import Guardian
from app.models.audit_log import AuditLog
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    """Registers a new user account with role-specific profile (PATIENT, DOCTOR, GUARDIAN)."""
    role = user_in.role.upper()
    if role not in ["PATIENT", "DOCTOR", "GUARDIAN", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be PATIENT, DOCTOR, or GUARDIAN."
        )

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == user_in.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered."
        )

    user_id = f"U{uuid.uuid4().hex[:8].upper()}"
    new_user = User(
        id=user_id,
        name=user_in.name,
        email=user_in.email.lower(),
        password_hash=hash_password(user_in.password),
        role=role,
        is_active=True,
    )
    db.add(new_user)

    # Create role profile
    if role == "PATIENT":
        patient_id = f"P{uuid.uuid4().hex[:6].upper()}"
        patient = Patient(
            id=patient_id,
            user_id=user_id,
            age=user_in.age or 35,
            gender=user_in.gender or "Unspecified",
            conditions=[],
            medications=[],
            allergies=[],
        )
        db.add(patient)
    elif role == "DOCTOR":
        doctor_id = f"D{uuid.uuid4().hex[:6].upper()}"
        doctor = Doctor(
            id=doctor_id,
            user_id=user_id,
            specialty=user_in.specialty or "General Practice",
            hospital=user_in.hospital or "Central Hospital",
            qualifications=user_in.qualifications or "MBBS",
        )
        db.add(doctor)
    elif role == "GUARDIAN":
        guardian_id = f"G{uuid.uuid4().hex[:6].upper()}"
        guardian = Guardian(
            id=guardian_id,
            user_id=user_id,
            linked_patient_id=user_in.linked_patient_id or "",
            relationship=user_in.relationship or "Guardian",
        )
        db.add(guardian)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=user_id,
        actor_role=role,
        action="USER_REGISTERED",
        target_type="USER",
        target_id=user_id,
        details=f"User {user_in.name} registered with role {role}",
    )
    db.add(audit)
    await db.commit()

    token = create_access_token(subject=user_id, role=role)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(new_user)
    )

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticates user and returns JWT token."""
    result = await db.execute(select(User).where(User.email == credentials.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated."
        )

    token = create_access_token(subject=user.id, role=user.role)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=user.id,
        actor_role=user.role,
        action="USER_LOGGED_IN",
        target_type="USER",
        target_id=user.id,
        details=f"Successful login for {user.email}",
    )
    db.add(audit)
    await db.commit()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns currently authenticated user profile."""
    return current_user
