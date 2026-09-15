"""Clinical diagnosis entry model."""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. DX501
    patient_id: Mapped[str] = mapped_column(String(50), ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[str] = mapped_column(String(50), ForeignKey("doctors.id"), nullable=False)
    diagnosis_name: Mapped[str] = mapped_column(String(200), nullable=False)
    clinical_note: Mapped[str] = mapped_column(Text, nullable=False)
    medication: Mapped[str | None] = mapped_column(String(150), nullable=True)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disclose_to_patient: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disclosure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_facing_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    guardian_notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
