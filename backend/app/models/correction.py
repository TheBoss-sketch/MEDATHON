"""Patient history correction suggestion model."""
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. CORR301
    patient_id: Mapped[str] = mapped_column(String(50), ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("doctors.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # MEDICATION, CONDITION, ALLERGY, OTHER
    current_value: Mapped[str] = mapped_column(String(200), nullable=False)
    suggested_value: Mapped[str] = mapped_column(String(200), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)  # PENDING, ACCEPTED, DISMISSED
    dismissal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
