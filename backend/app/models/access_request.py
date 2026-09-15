"""Doctor-to-patient record access request model."""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AccessRequest(Base):
    __tablename__ = "access_requests"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. AR1001
    doctor_id: Mapped[str] = mapped_column(String(50), ForeignKey("doctors.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(50), ForeignKey("patients.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)  # PENDING, APPROVED, DENIED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
