"""In-app user notification model."""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)  # e.g. NOTIF401
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # FLAG_ALERT, ACCESS_REQUEST, ACCESS_APPROVED, CORRECTION, etc.
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Links to flag_id, diagnosis_id, etc.
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
