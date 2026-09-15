"""Alert delivery tracking model."""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    flag_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("flags.id"), nullable=True)
    recipient_user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. ESP32_PAGER
    channel: Mapped[str] = mapped_column(String(30), nullable=False)  # PAGER, DASHBOARD, INBOX, EMAIL
    status: Mapped[str] = mapped_column(String(30), default="SENT", nullable=False)  # SENT, DELIVERED, ACKNOWLEDGED
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
