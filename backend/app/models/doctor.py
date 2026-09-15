"""Doctor entity model."""
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. D101
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), unique=True, nullable=False)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False)
    hospital: Mapped[str] = mapped_column(String(150), nullable=False)
    qualifications: Mapped[str] = mapped_column(String(100), nullable=False)
    pager_device_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Physical pager association
