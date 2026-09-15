"""Clinical flags triage and resolution lifecycle endpoints."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, case

from app.db.session import get_db
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.diagnosis import Diagnosis
from app.models.flag import Flag
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.schemas.flag import FlagOut, FlagResolveRequest, FlagDismissRequest, FlagSummaryStats
from app.core.deps import get_current_user, require_roles

router = APIRouter(prefix="/flags", tags=["flags"])

@router.get("/stats", response_model=FlagSummaryStats)
async def get_flag_stats(
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN", "GUARDIAN"])),
    db: AsyncSession = Depends(get_db)
):
    """Returns aggregated severity and status counts for the clinical command center."""
    all_flags_res = await db.execute(select(Flag))
    flags = all_flags_res.scalars().all()

    active_flags = [f for f in flags if f.status in ["OPEN", "UNDER_REVIEW"]]
    high_count = sum(1 for f in active_flags if f.severity == "HIGH")
    med_count = sum(1 for f in active_flags if f.severity == "MEDIUM")
    low_count = sum(1 for f in active_flags if f.severity == "LOW")
    under_review_count = sum(1 for f in flags if f.status == "UNDER_REVIEW")
    resolved_count = sum(1 for f in flags if f.status == "RESOLVED")

    return FlagSummaryStats(
        total_active=len(active_flags),
        high_priority=high_count,
        medium_priority=med_count,
        low_priority=low_count,
        under_review=under_review_count,
        resolved_today=resolved_count,
    )

@router.get("", response_model=List[FlagOut])
async def list_flags(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity_filter: Optional[str] = Query(None, alias="severity"),
    patient_id: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN", "GUARDIAN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists clinical reconciliation flags sorted primarily by priority (HIGH -> MEDIUM -> LOW),
    then by recency. Supports filtering by status and severity.
    """
    # Priority sorting expression
    severity_order = case(
        (Flag.severity == "HIGH", 1),
        (Flag.severity == "MEDIUM", 2),
        (Flag.severity == "LOW", 3),
        else_=4
    )

    query = select(Flag)
    filters = []

    if status_filter:
        filters.append(Flag.status == status_filter.upper())
    if severity_filter:
        filters.append(Flag.severity == severity_filter.upper())
    if patient_id:
        filters.append(Flag.patient_id == patient_id)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(severity_order, desc(Flag.created_at))
    rows = await db.execute(query)
    flags = rows.scalars().all()

    output = []
    for f in flags:
        # Resolve patient name
        p_res = await db.execute(select(Patient).where(Patient.id == f.patient_id))
        pat = p_res.scalar_one_or_none()
        pat_name = "Patient"
        if pat:
            pu_res = await db.execute(select(User).where(User.id == pat.user_id))
            pu = pu_res.scalar_one_or_none()
            if pu:
                pat_name = pu.name

        # Resolve diagnosis name
        d_res = await db.execute(select(Diagnosis).where(Diagnosis.id == f.diagnosis_id))
        diag = d_res.scalar_one_or_none()
        diag_name = diag.diagnosis_name if diag else "Diagnosis"

        output.append(FlagOut(
            id=f.id,
            patient_id=f.patient_id,
            patient_name=pat_name,
            diagnosis_id=f.diagnosis_id,
            diagnosis_name=diag_name,
            historical_reference=f.historical_reference,
            root_cause=f.root_cause,
            severity=f.severity,
            status=f.status,
            explanation=f.explanation,
            resolution_note=f.resolution_note,
            created_at=f.created_at,
            resolved_at=f.resolved_at
        ))
    return output

@router.post("/{flag_id}/review", response_model=FlagOut)
async def mark_flag_under_review(
    flag_id: str,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Doctor claims flag and transitions it to UNDER_REVIEW."""
    res = await db.execute(select(Flag).where(Flag.id == flag_id))
    flag = res.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found.")

    flag.status = "UNDER_REVIEW"

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role="DOCTOR",
        action="FLAG_UNDER_REVIEW",
        target_type="FLAG",
        target_id=flag.id,
        details=f"Dr. {current_user.name} initiated clinical review for flag {flag.id}",
    )
    db.add(audit)
    await db.commit()

    return FlagOut.model_validate(flag)

@router.post("/{flag_id}/resolve", response_model=FlagOut)
async def resolve_flag(
    flag_id: str,
    req_in: FlagResolveRequest,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Doctor resolves a flag with clinical action documentation."""
    res = await db.execute(select(Flag).where(Flag.id == flag_id))
    flag = res.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found.")

    flag.status = "RESOLVED"
    flag.resolution_note = req_in.resolution_note
    flag.resolved_at = datetime.now(timezone.utc)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role="DOCTOR",
        action="FLAG_RESOLVED",
        target_type="FLAG",
        target_id=flag.id,
        details=f"Dr. {current_user.name} resolved flag with note: {req_in.resolution_note}",
    )
    db.add(audit)
    await db.commit()

    return FlagOut.model_validate(flag)

@router.post("/{flag_id}/dismiss", response_model=FlagOut)
async def dismiss_flag(
    flag_id: str,
    req_in: FlagDismissRequest,
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Doctor dismisses a flag with clinical justification (e.g. acceptable clinical variance)."""
    res = await db.execute(select(Flag).where(Flag.id == flag_id))
    flag = res.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found.")

    flag.status = "DISMISSED"
    flag.resolution_note = f"Dismissed: {req_in.dismissal_reason}"
    flag.resolved_at = datetime.now(timezone.utc)

    # Audit log
    audit = AuditLog(
        id=f"AUD{uuid.uuid4().hex[:8].upper()}",
        actor_id=current_user.id,
        actor_role="DOCTOR",
        action="FLAG_DISMISSED",
        target_type="FLAG",
        target_id=flag.id,
        details=f"Dr. {current_user.name} dismissed flag with reason: {req_in.dismissal_reason}",
    )
    db.add(audit)
    await db.commit()

    return FlagOut.model_validate(flag)
