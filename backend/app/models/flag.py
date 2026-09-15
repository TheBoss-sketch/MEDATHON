"""Clinical reconciliation flag entity model."""
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. F101
    patient_id: Mapped[str] = mapped_column(String(50), ForeignKey("patients.id"), nullable=False)
    diagnosis_id: Mapped[str] = mapped_column(String(50), ForeignKey("diagnoses.id"), nullable=False)
    historical_reference: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(String(50), nullable=False)  # doctor_gap, patient_gap, no_fault, intentional
    severity: Mapped[str] = mapped_column(String(20), nullable=False)    # LOW, MEDIUM, HIGH
    status: Mapped[str] = mapped_column(String(30), default="OPEN", nullable=False)  # OPEN, UNDER_REVIEW, RESOLVED, DISMISSED
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
