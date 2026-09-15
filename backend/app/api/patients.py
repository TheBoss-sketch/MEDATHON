"""Patient profile, history timeline, and access authorization endpoints."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.db.session import get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.guardian import Guardian
from app.models.access_request import AccessRequest
from app.models.diagnosis import Diagnosis
from app.models.flag import Flag
from app.models.correction import Correction
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.schemas.patient import (
    PatientOut,
    PatientTimelineItem,
    PatientHistoryOut,
    AccessRequestCreate,
    AccessRequestRespond,
    AccessRequestOut,
)
from app.core.deps import get_current_user, require_roles

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("", response_model=List[PatientOut])
async def list_patients(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists accessible patients depending on the caller's role."""
    if current_user.role == "PATIENT":
        result = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = result.scalar_one_or_none()
        if not patient:
            return []
        p_out = PatientOut.model_validate(patient)
        p_out.name = current_user.name
        p_out.email = current_user.email
        return [p_out]

    elif current_user.role == "GUARDIAN":
        g_res = await db.execute(select(Guardian).where(Guardian.user_id == current_user.id))
        guardian = g_res.scalar_one_or_none()
        if not guardian or not guardian.linked_patient_id:
            return []
        result = await db.execute(select(Patient).where(Patient.id == guardian.linked_patient_id))
        patient = result.scalar_one_or_none()
        if not patient:
            return []
        u_res = await db.execute(select(User).where(User.id == patient.user_id))
        u = u_res.scalar_one_or_none()
        p_out = PatientOut.model_validate(patient)
        p_out.name = u.name if u else "Patient"
        p_out.email = u.email if u else None
        return [p_out]

    elif current_user.role in ["DOCTOR", "ADMIN"]:
        # Return all registered patients for clinical selection
        result = await db.execute(select(Patient))
        patients = result.scalars().all()
        output = []
        for p in patients:
            u_res = await db.execute(select(User).where(User.id == p.user_id))
            u = u_res.scalar_one_or_none()
            p_out = PatientOut.model_validate(p)
            p_out.name = u.name if u else "Unknown Patient"
            p_out.email = u.email if u else None
            output.append(p_out)
        return output

    return []

@router.get("/{patient_id}/timeline", response_model=PatientHistoryOut)
async def get_patient_timeline(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves patient medical history timeline with granular access and disclosure filtering."""
    p_res = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = p_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    u_res = await db.execute(select(User).where(User.id == patient.user_id))
    patient_user = u_res.scalar_one_or_none()

    has_full_access = False
    is_patient_self = current_user.id == patient.user_id
    is_admin = current_user.role == "ADMIN"

    # Access check
    if is_patient_self or is_admin:
        has_full_access = True
    elif current_user.role == "GUARDIAN":
        g_res = await db.execute(
            select(Guardian).where(
                and_(Guardian.user_id == current_user.id, Guardian.linked_patient_id == patient_id)
            )
        )
        if g_res.scalar_one_or_none():
            has_full_access = True
    elif current_user.role == "DOCTOR":
        d_res = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
        doctor = d_res.scalar_one_or_none()
        if doctor:
            # Verify approved access request
            ar_res = await db.execute(
                select(AccessRequest).where(
                    and_(
                        AccessRequest.doctor_id == doctor.id,
                        AccessRequest.patient_id == patient_id,
                        AccessRequest.status == "APPROVED"
                    )
                )
            )
            if ar_res.scalar_one_or_none():
                has_full_access = True

    timeline: List[PatientTimelineItem] = []

    # Known conditions, medications, allergies (if accessible)
    if has_full_access or current_user.role == "DOCTOR":
        for cond in patient.conditions or []:
            timeline.append(PatientTimelineItem(
                date=patient.created_at,
                type="CONDITION",
                title=f"Chronic Condition: {cond}",
                description="Recorded in patient profile"
            ))
        for med in patient.medications or []:
            timeline.append(PatientTimelineItem(
                date=patient.created_at,
                type="MEDICATION",
                title=f"Active Rx: {med}",
                description="Current patient medication"
            ))
        for alg in patient.allergies or []:
            timeline.append(PatientTimelineItem(
                date=patient.created_at,
                type="ALLERGY",
                title=f"Allergy Alert: {alg}",
                description="Documented adverse allergic reaction",
                severity="HIGH"
            ))

    # Diagnoses query
    diag_query = select(Diagnosis).where(Diagnosis.patient_id == patient_id)
    # If caller is the patient directly, filter out withheld diagnoses (therapeutic privilege)
    if is_patient_self:
        diag_query = diag_query.where(Diagnosis.disclose_to_patient == True)
    
    d_rows = await db.execute(diag_query.order_by(desc(Diagnosis.created_at)))
    diagnoses = d_rows.scalars().all()

    for d in diagnoses:
        title = f"Diagnosis: {d.diagnosis_name}"
        desc_text = d.patient_facing_text if (is_patient_self and d.patient_facing_text) else d.clinical_note
        if d.medication:
            desc_text += f" | Prescribed: {d.medication} ({d.dosage or 'Standard'})"

        if not d.disclose_to_patient:
            title += " [Withheld from Patient]"
            desc_text += f" | Withholding reason: {d.disclosure_reason or 'Therapeutic privilege'}"

        timeline.append(PatientTimelineItem(
            date=d.created_at,
            type="DIAGNOSIS",
            title=title,
            description=desc_text,
            metadata={
                "diagnosis_id": d.id,
                "doctor_id": d.doctor_id,
                "disclose_to_patient": d.disclose_to_patient,
                "disclosure_reason": d.disclosure_reason
            }
        ))

    # Flags (visible to doctors, guardians, and admins)
    if current_user.role in ["DOCTOR", "GUARDIAN", "ADMIN"]:
        f_rows = await db.execute(
            select(Flag).where(Flag.patient_id == patient_id).order_by(desc(Flag.created_at))
        )
        flags = f_rows.scalars().all()
        for f in flags:
            timeline.append(PatientTimelineItem(
                date=f.created_at,
                type="FLAG",
                title=f"Reconciliation Flag [{f.severity}]: {f.root_cause}",
                description=f"{f.explanation} (Status: {f.status})",
                severity=f.severity,
                metadata={"flag_id": f.id, "status": f.status}
            ))

    # Sort timeline chronologically descending
    timeline.sort(key=lambda item: item.date, reverse=True)

    patient_out = PatientOut.model_validate(patient)
    patient_out.name = patient_user.name if patient_user else "Patient"
    patient_out.email = patient_user.email if patient_user else None

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role=current_user.role,
        action="VIEW_PATIENT_TIMELINE",
        target_type="PATIENT",
        target_id=patient_id,
        details=f"Viewed timeline. full_access={has_full_access}",
    )
    db.add(audit)
    await db.commit()

    return PatientHistoryOut(
        patient=patient_out,
        timeline=timeline,
        has_full_access=has_full_access
    )

# ----------------------------------------------------------------------------
# Access Authorization Workflows
# ----------------------------------------------------------------------------
@router.post("/access-requests", response_model=AccessRequestOut, status_code=status.HTTP_201_CREATED)
async def request_patient_access(
    req_in: AccessRequestCreate,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Doctor requests authorized access to patient medical records."""
    d_res = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
    doctor = d_res.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found.")

    p_res = await db.execute(select(Patient).where(Patient.id == req_in.patient_id))
    patient = p_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # Check if already approved or pending
    existing = await db.execute(
        select(AccessRequest).where(
            and_(
                AccessRequest.doctor_id == doctor.id,
                AccessRequest.patient_id == req_in.patient_id,
                AccessRequest.status.in_(["PENDING", "APPROVED"])
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="An access request is already pending or approved for this patient."
        )

    req_id = f"AR{uuid.uuid4().hex[:6].upper()}"
    new_req = AccessRequest(
        id=req_id,
        doctor_id=doctor.id,
        patient_id=req_in.patient_id,
        status="PENDING",
        notes=req_in.notes or "Consultation access request"
    )
    db.add(new_req)

    # Send Notification to patient
    notif = Notification(
        id=f"NOTIF{uuid.uuid4().hex[:6].upper()}",
        user_id=patient.user_id,
        type="ACCESS_REQUEST",
        title="New Medical Record Access Request",
        message=f"Dr. {current_user.name} ({doctor.specialty}) has requested access to your medical history.",
        related_id=req_id
    )
    db.add(notif)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role="DOCTOR",
        action="ACCESS_REQUEST_SUBMITTED",
        target_type="PATIENT",
        target_id=req_in.patient_id,
        details=f"Doctor {current_user.name} requested access",
    )
    db.add(audit)
    await db.commit()

    return AccessRequestOut(
        id=new_req.id,
        doctor_id=doctor.id,
        doctor_name=current_user.name,
        doctor_specialty=doctor.specialty,
        patient_id=patient.id,
        status=new_req.status,
        notes=new_req.notes,
        requested_at=new_req.requested_at,
        responded_at=new_req.responded_at
    )

@router.get("/access-requests/list", response_model=List[AccessRequestOut])
async def list_access_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists access requests relevant to current user (Patient sees incoming, Doctor sees outgoing)."""
    if current_user.role == "PATIENT":
        p_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = p_res.scalar_one_or_none()
        if not patient:
            return []
        query = select(AccessRequest).where(AccessRequest.patient_id == patient.id)
    elif current_user.role == "DOCTOR":
        d_res = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
        doctor = d_res.scalar_one_or_none()
        if not doctor:
            return []
        query = select(AccessRequest).where(AccessRequest.doctor_id == doctor.id)
    else:
        query = select(AccessRequest)

    rows = await db.execute(query.order_by(desc(AccessRequest.requested_at)))
    requests = rows.scalars().all()

    output = []
    for r in requests:
        # Fetch names
        d_res = await db.execute(select(Doctor).where(Doctor.id == r.doctor_id))
        doc = d_res.scalar_one_or_none()
        doc_user = None
        if doc:
            du_res = await db.execute(select(User).where(User.id == doc.user_id))
            doc_user = du_res.scalar_one_or_none()

        p_res = await db.execute(select(Patient).where(Patient.id == r.patient_id))
        pat = p_res.scalar_one_or_none()
        pat_user = None
        if pat:
            pu_res = await db.execute(select(User).where(User.id == pat.user_id))
            pat_user = pu_res.scalar_one_or_none()

        output.append(AccessRequestOut(
            id=r.id,
            doctor_id=r.doctor_id,
            doctor_name=doc_user.name if doc_user else "Doctor",
            doctor_specialty=doc.specialty if doc else "Specialist",
            patient_id=r.patient_id,
            patient_name=pat_user.name if pat_user else "Patient",
            status=r.status,
            notes=r.notes,
            requested_at=r.requested_at,
            responded_at=r.responded_at
        ))
    return output

@router.post("/access-requests/{request_id}/respond", response_model=AccessRequestOut)
async def respond_to_access_request(
    request_id: str,
    response_in: AccessRequestRespond,
    current_user: User = Depends(require_roles(["PATIENT", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Patient approves or denies an access request."""
    result = await db.execute(select(AccessRequest).where(AccessRequest.id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Access request not found.")

    if current_user.role == "PATIENT":
        p_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
        patient = p_res.scalar_one_or_none()
        if not patient or req.patient_id != patient.id:
            raise HTTPException(status_code=403, detail="Unauthorized to respond to this request.")

    new_status = "APPROVED" if response_in.approve else "DENIED"
    req.status = new_status
    req.responded_at = datetime.now(timezone.utc)

    # Notify doctor
    d_res = await db.execute(select(Doctor).where(Doctor.id == req.doctor_id))
    doctor = d_res.scalar_one_or_none()
    if doctor:
        notif = Notification(
            id=f"NOTIF{uuid.uuid4().hex[:6].upper()}",
            user_id=doctor.user_id,
            type=f"ACCESS_{new_status}",
            title=f"Access Request {new_status.title()}",
            message=f"Your access request for Patient {req.patient_id} was {new_status.lower()}.",
            related_id=req.id
        )
        db.add(notif)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role=current_user.role,
        action=f"ACCESS_REQUEST_{new_status}",
        target_type="ACCESS_REQUEST",
        target_id=req.id,
        details=f"Access request {new_status.lower()} by patient {req.patient_id}",
    )
    db.add(audit)
    await db.commit()

    return AccessRequestOut(
        id=req.id,
        doctor_id=req.doctor_id,
        patient_id=req.patient_id,
        status=req.status,
        notes=req.notes,
        requested_at=req.requested_at,
        responded_at=req.responded_at
    )
