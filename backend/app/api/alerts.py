"""Clinical Alert API endpoints."""
from fastapi import APIRouter, status
from app.schemas.alert import MedreaAlert, AlertDispatchResponse
from app.services.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.post("/test", response_model=AlertDispatchResponse, status_code=status.HTTP_200_OK)
async def trigger_test_alert(alert: MedreaAlert):
    """
    Ingests a test clinical reconciliation alert and dispatches it
    to all active delivery channels (ESP32 pager, dashboards).
    """
    delivered_count = await alert_service.dispatch_alert(alert)

    return AlertDispatchResponse(
        status="dispatched",
        alert=alert,
        delivered_to_pagers=delivered_count
    )
