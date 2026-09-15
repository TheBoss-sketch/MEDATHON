"""Clinical diagnosis intake and post-diagnosis reconciliation trigger."""
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
from app.models.guardian import Guardian
from app.models.diagnosis import Diagnosis
from app.models.flag import Flag
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.alert_delivery import AlertDelivery
from app.schemas.diagnosis import DiagnosisCreate, DiagnosisOut
from app.schemas.alert import MedreaAlert, AlertSeverity
from app.services.alert_service import alert_service
from app.services.reconciliation_boundary import reconciliation_engine
from app.core.deps import get_current_user, require_roles

router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])

@router.post("", response_model=DiagnosisOut, status_code=status.HTTP_201_CREATED)
async def create_diagnosis(
    diag_in: DiagnosisCreate,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Intakes a new clinical diagnosis, checks therapeutic disclosure preferences,
    evaluates post-diagnosis reconciliation, and triggers hardware pager alerts for high-severity flags.
    """
    # Fetch doctor profile
    d_res = await db.execute(select(Doctor).where(Doctor.user_id == current_user.id))
    doctor = d_res.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=400, detail="Doctor profile not found.")

    # Fetch patient profile
    p_res = await db.execute(select(Patient).where(Patient.id == diag_in.patient_id))
    patient = p_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # Validate therapeutic privilege / disclosure reason
    guardian_notified = False
    if not diag_in.disclose_to_patient:
        if not diag_in.disclosure_reason or len(diag_in.disclosure_reason.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Disclosure reason is required when withholding diagnosis from direct patient view (e.g. therapeutic privilege)."
            )

        # Look up linked guardian to notify
        g_res = await db.execute(select(Guardian).where(Guardian.linked_patient_id == patient.id))
        guardian = g_res.scalar_one_or_none()
        if guardian:
            g_notif = Notification(
                id=f"NOTIF{uuid.uuid4().hex[:6].upper()}",
                user_id=guardian.user_id,
                type="WITHHELD_DIAGNOSIS",
                title="Confidential Clinical Update for Dependent Patient",
                message=(
                    f"Dr. {current_user.name} logged a diagnosis for your dependent. "
                    f"Direct disclosure is staged: '{diag_in.disclosure_reason}'. "
                    f"Diagnosis: {diag_in.diagnosis_name}"
                )
            )
            db.add(g_notif)
            guardian_notified = True

    # Save Diagnosis record
    diag_id = f"DX{uuid.uuid4().hex[:6].upper()}"
    diagnosis = Diagnosis(
        id=diag_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        diagnosis_name=diag_in.diagnosis_name,
        clinical_note=diag_in.clinical_note,
        medication=diag_in.medication,
        dosage=diag_in.dosage,
        disclose_to_patient=diag_in.disclose_to_patient,
        disclosure_reason=diag_in.disclosure_reason,
        patient_facing_text=diag_in.patient_facing_text,
        guardian_notified=guardian_notified,
    )
    db.add(diagnosis)
    await db.flush()

    # Retrieve prior diagnoses for reconciliation
    prior_res = await db.execute(
        select(Diagnosis).where(
            and_(Diagnosis.patient_id == patient.id, Diagnosis.id != diag_id)
        ).order_by(desc(Diagnosis.created_at))
    )
    prior_diagnoses = list(prior_res.scalars().all())

    # Evaluate Reconciliation through service boundary
    results = await reconciliation_engine.evaluate_reconciliation(
        new_diagnosis=diagnosis,
        patient=patient,
        prior_diagnoses=prior_diagnoses
    )

    generated_flag_ids: List[str] = []

    for res in results:
        if res.has_flag:
            flag_id = f"F{uuid.uuid4().hex[:6].upper()}"
            flag = Flag(
                id=flag_id,
                patient_id=patient.id,
                diagnosis_id=diagnosis.id,
                historical_reference=res.historical_reference,
                root_cause=res.root_cause,
                severity=res.severity,
                status="OPEN",
                explanation=res.explanation,
            )
            db.add(flag)
            generated_flag_ids.append(flag_id)

            # In-app notification for doctor
            d_notif = Notification(
                id=f"NOTIF{uuid.uuid4().hex[:6].upper()}",
                user_id=current_user.id,
                type="FLAG_ALERT",
                title=f"Clinical Flag [{res.severity}]: {res.root_cause}",
                message=f"Flag generated for Patient {patient.id}: {res.explanation}",
                related_id=flag_id
            )
            db.add(d_notif)

            # Trigger Hardware Alert via AlertService if HIGH severity
            if res.severity == "HIGH":
                alert_packet = MedreaAlert(
                    type="MEDREA_ALERT",
                    severity=AlertSeverity.HIGH,
                    patient_id=patient.id,
                    message=res.explanation[:60],
                    diagnosis=diagnosis.diagnosis_name,
                    medication=diagnosis.medication
                )
                delivered_count = await alert_service.dispatch_alert(alert_packet)

                # Record delivery telemetry
                delivery = AlertDelivery(
                    id=f"AD{uuid.uuid4().hex[:6].upper()}",
                    flag_id=flag_id,
                    recipient_user_id=current_user.id,
                    device_id="ESP32_PAGER",
                    channel="PAGER",
                    status="DELIVERED" if delivered_count > 0 else "SENT",
                )
                db.add(delivery)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role="DOCTOR",
        action="DIAGNOSIS_LOGGED",
        target_type="DIAGNOSIS",
        target_id=diag_id,
        details=(
            f"Diagnosis: {diagnosis.diagnosis_name} for patient {patient.id}. "
            f"Flags generated: {len(generated_flag_ids)}"
        )
    )
    db.add(audit)
    await db.commit()

    return DiagnosisOut(
        id=diagnosis.id,
        patient_id=diagnosis.patient_id,
        doctor_id=diagnosis.doctor_id,
        doctor_name=current_user.name,
        diagnosis_name=diagnosis.diagnosis_name,
        clinical_note=diagnosis.clinical_note,
        medication=diagnosis.medication,
        dosage=diagnosis.dosage,
        disclose_to_patient=diagnosis.disclose_to_patient,
        disclosure_reason=diagnosis.disclosure_reason,
        patient_facing_text=diagnosis.patient_facing_text,
        guardian_notified=diagnosis.guardian_notified,
        created_at=diagnosis.created_at,
        generated_flags=generated_flag_ids
    )

@router.get("/patient/{patient_id}", response_model=List[DiagnosisOut])
async def list_diagnoses_for_patient(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists diagnoses for a patient respecting privacy and disclosure staging."""
    query = select(Diagnosis).where(Diagnosis.patient_id == patient_id)

    # If the caller is the patient themselves, filter out non-disclosed diagnoses
    p_res = await db.execute(select(Patient).where(Patient.user_id == current_user.id))
    caller_patient = p_res.scalar_one_or_none()
    if caller_patient and caller_patient.id == patient_id:
        query = query.where(Diagnosis.disclose_to_patient == True)

    rows = await db.execute(query.order_by(desc(Diagnosis.created_at)))
    diagnoses = rows.scalars().all()

    output = []
    for d in diagnoses:
        # Resolve doctor name
        doc_res = await db.execute(select(Doctor).where(Doctor.id == d.doctor_id))
        doc = doc_res.scalar_one_or_none()
        doc_name = "Doctor"
        if doc:
            du_res = await db.execute(select(User).where(User.id == doc.user_id))
            du = du_res.scalar_one_or_none()
            if du:
                doc_name = du.name

        output.append(DiagnosisOut(
            id=d.id,
            patient_id=d.patient_id,
            doctor_id=d.doctor_id,
            doctor_name=doc_name,
            diagnosis_name=d.diagnosis_name,
            clinical_note=d.clinical_note,
            medication=d.medication,
            dosage=d.dosage,
            disclose_to_patient=d.disclose_to_patient,
            disclosure_reason=d.disclosure_reason,
            patient_facing_text=d.patient_facing_text,
            guardian_notified=d.guardian_notified,
            created_at=d.created_at,
            generated_flags=[]
        ))
    return output
