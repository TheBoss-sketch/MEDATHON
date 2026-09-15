"""Patient correction suggestions and clinical review endpoints."""
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.db.session import get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.correction import Correction
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.schemas.correction import CorrectionCreate, CorrectionDismissRequest, CorrectionOut
from app.core.deps import get_current_user, require_roles

router = APIRouter(prefix="/corrections", tags=["corrections"])

@router.post("", response_model=CorrectionOut, status_code=status.HTTP_201_CREATED)
async def submit_correction(
    corr_in: CorrectionCreate,
    current_user: User = Depends(require_roles(["PATIENT", "GUARDIAN", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Patient or guardian suggests a correction to their historical medical record."""
    target_patient_id = corr_in.patient_id

    if current_user.role == "PATIENT":
        p_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = p_res.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=400, detail="Patient profile not found.")
        target_patient_id = patient.id
    else:
        if not target_patient_id:
            raise HTTPException(status_code=400, detail="Patient ID is required.")
        p_res = await db.execute(select(Patient).where(Patient.id == target_patient_id))
        patient = p_res.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

    corr_id = f"CORR{uuid.uuid4().hex[:6].upper()}"
    correction = Correction(
        id=corr_id,
        patient_id=target_patient_id,
        entity_type=corr_in.entity_type.upper(),
        current_value=corr_in.current_value,
        suggested_value=corr_in.suggested_value,
        note=corr_in.note,
        status="PENDING",
    )
    db.add(correction)

    # Notify doctors treating this patient
    # Broadcast in-app notification to all active doctors or clinical staff
    d_rows = await db.execute(select(Doctor))
    doctors = d_rows.scalars().all()
    for d in doctors:
        notif = Notification(
            id=f"NOTIF{uuid.uuid4().hex[:6].upper()}",
            user_id=d.user_id,
            type="CORRECTION_SUBMITTED",
            title="Patient Correction Pending Review",
            message=f"Patient {target_patient_id} suggested updating {corr_in.entity_type}: '{corr_in.suggested_value}' ({corr_in.note})",
            related_id=corr_id
        )
        db.add(notif)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="CORRECTION_SUBMITTED",
        target_type="CORRECTION",
        target_id=corr_id,
        details=f"Correction suggested for {corr_in.entity_type}: {corr_in.current_value} -> {corr_in.suggested_value}",
    )
    db.add(audit)
    await db.commit()

    return CorrectionOut.model_validate(correction)

@router.get("", response_model=List[CorrectionOut])
async def list_corrections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists corrections relevant to the caller."""
    if current_user.role == "PATIENT":
        p_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = p_res.scalar_one_or_none()
        if not patient:
            return []
        query = select(Correction).where(Correction.patient_id == patient.id)
    else:
        query = select(Correction)

    rows = await db.execute(query.order_by(desc(Correction.created_at)))
    corrections = rows.scalars().all()

    output = []
    for c in corrections:
        # Resolve patient name
        p_res = await db.execute(select(Patient).where(Patient.id == c.patient_id))
        pat = p_res.scalar_one_or_none()
        p_name = "Patient"
        if pat:
            pu_res = await db.execute(select(User).where(User.id == pat.user_id))
            pu = pu_res.scalar_one_or_none()
            if pu:
                p_name = pu.name

        output.append(CorrectionOut(
            id=c.id,
            patient_id=c.patient_id,
            patient_name=p_name,
            doctor_id=c.doctor_id,
            entity_type=c.entity_type,
            current_value=c.current_value,
            suggested_value=c.suggested_value,
            note=c.note,
            status=c.status,
            dismissal_reason=c.dismissal_reason,
            created_at=c.created_at,
            reviewed_at=c.reviewed_at
        ))
    return output

@router.post("/{corr_id}/accept", response_model=CorrectionOut)
async def accept_correction(
    corr_id: str,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Doctor reviews and accepts a correction, applying the change to patient history."""
    c_res = await db.execute(select(Correction).where(Correction.id == corr_id))
    correction = c_res.scalar_one_or_none()
    if not correction:
        raise HTTPException(status_code=404, detail="Correction not found.")

    p_res = await db.execute(select(Patient).where(Patient.id == correction.patient_id))
    patient = p_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Target patient record not found.")

    correction.status = "ACCEPTED"
    correction.reviewed_at = datetime.now(timezone.utc)
    correction.doctor_id = current_user.id

    # Apply correction to patient history record
    entity = correction.entity_type.upper()
    if entity == "MEDICATION":
        meds = list(patient.medications or [])
        # Replace or update
        if correction.current_value in meds:
            meds.remove(correction.current_value)
        if correction.suggested_value not in meds and correction.suggested_value.lower() != "discontinued":
            meds.append(correction.suggested_value)
        patient.medications = meds
    elif entity == "ALLERGY":
        allergies = list(patient.allergies or [])
        if correction.current_value in allergies:
            allergies.remove(correction.current_value)
        if correction.suggested_value not in allergies:
            allergies.append(correction.suggested_value)
        patient.allergies = allergies
    elif entity == "CONDITION":
        conds = list(patient.conditions or [])
        if correction.current_value in conds:
            conds.remove(correction.current_value)
        if correction.suggested_value not in conds:
            conds.append(correction.suggested_value)
        patient.conditions = conds

    # Notify patient
    notif = Notification(
        id=f"NOTIF{uuid.uuid4().hex[:6].upper()}",
        user_id=patient.user_id,
        type="CORRECTION_ACCEPTED",
        title="Correction Suggestion Approved",
        message=f"Dr. {current_user.name} reviewed and accepted your update for {correction.entity_type}: '{correction.suggested_value}'. Your clinical record has been updated.",
        related_id=corr_id
    )
    db.add(notif)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role="DOCTOR",
        action="CORRECTION_ACCEPTED",
        target_type="CORRECTION",
        target_id=corr_id,
        details=f"Dr. {current_user.name} accepted correction {corr_id} for Patient {patient.id}",
    )
    db.add(audit)
    await db.commit()

    return CorrectionOut.model_validate(correction)

@router.post("/{corr_id}/dismiss", response_model=CorrectionOut)
async def dismiss_correction(
    corr_id: str,
    req_in: CorrectionDismissRequest,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Doctor dismisses a correction suggestion with a clinical explanation."""
    c_res = await db.execute(select(Correction).where(Correction.id == corr_id))
    correction = c_res.scalar_one_or_none()
    if not correction:
        raise HTTPException(status_code=404, detail="Correction not found.")

    p_res = await db.execute(select(Patient).where(Patient.id == correction.patient_id))
    patient = p_res.scalar_one_or_none()

    correction.status = "DISMISSED"
    correction.dismissal_reason = req_in.dismissal_reason
    correction.reviewed_at = datetime.now(timezone.utc)
    correction.doctor_id = current_user.id

    # Notify patient
    if patient:
        notif = Notification(
            id=f"NOTIF{uuid.uuid4().hex[:6].upper()}",
            user_id=patient.user_id,
            type="CORRECTION_DISMISSED",
            title="Correction Suggestion Reviewed",
            message=f"Dr. {current_user.name} reviewed your suggestion for {correction.entity_type}. Reason: {req_in.dismissal_reason}",
            related_id=corr_id
        )
        db.add(notif)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role="DOCTOR",
        action="CORRECTION_DISMISSED",
        target_type="CORRECTION",
        target_id=corr_id,
        details=f"Dismissed with reason: {req_in.dismissal_reason}",
    )
    db.add(audit)
    await db.commit()

    return CorrectionOut.model_validate(correction)
