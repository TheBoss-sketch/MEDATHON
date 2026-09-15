"""Alert schemas for MEDREA."""
from enum import Enum
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class MedreaAlert(BaseModel):
    """Structured clinical alert model."""
    type: str = Field(default="MEDREA_ALERT", description="Message event type")
    severity: AlertSeverity = Field(default=AlertSeverity.HIGH, description="Alert priority level")
    patient_id: str = Field(..., description="Unique patient identifier")
    message: str = Field(..., description="Primary clinical conflict or notification summary")
    diagnosis: Optional[str] = Field(default=None, description="Current or related diagnosis")
    medication: Optional[str] = Field(default=None, description="Contradictory or prescribed medication")
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp"
    )

class AlertDispatchResponse(BaseModel):
    """Response returned when an alert is accepted and dispatched."""
    status: str
    alert: MedreaAlert
    delivered_to_pagers: int

class ClientAcknowledgment(BaseModel):
    """Schema prepared for future ESP32-to-backend acknowledgment packets."""
    type: str = Field(default="ALERT_ACK", description="Ack message identifier")
    patient_id: str
    status: str = Field(default="ACKNOWLEDGED", description="Acknowledgment state")
    device_ip: Optional[str] = None
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
