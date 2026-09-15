"""Patient entity model."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. P1042
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), unique=True, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    conditions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)   # e.g. ["Asthma"]
    medications: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # e.g. ["Salbutamol"]
    allergies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)    # e.g. ["Penicillin"]
    guardian_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
