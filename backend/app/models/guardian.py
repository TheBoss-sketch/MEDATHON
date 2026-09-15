"""Guardian caregiver entity model."""
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Guardian(Base):
    __tablename__ = "guardians"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. G201
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), unique=True, nullable=False)
    linked_patient_id: Mapped[str] = mapped_column(String(50), ForeignKey("patients.id"), nullable=False)
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)  # Mother, Spouse, Legal Guardian
