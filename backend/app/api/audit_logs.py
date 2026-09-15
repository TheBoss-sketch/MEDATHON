"""Clinical system audit logs API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.db.session import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogOut
from app.core.deps import get_current_user, require_roles

router = APIRouter(prefix="/audit-logs", tags=["audit"])

@router.get("", response_model=List[AuditLogOut])
async def list_audit_logs(
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(["DOCTOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves clinical action audit trail records for compliance and traceability."""
    query = select(AuditLog)
    filters = []

    if target_type:
        filters.append(AuditLog.target_type == target_type.upper())
    if target_id:
        filters.append(AuditLog.target_id == target_id)
    if action:
        filters.append(AuditLog.action == action.upper())

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(desc(AuditLog.timestamp)).limit(limit)
    rows = await db.execute(query)
    return rows.scalars().all()
