"""MEDREA Clinical Alert & Post-Diagnosis Reconciliation System - Main Entrypoint."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import init_db
from app.api.auth import router as auth_router
from app.api.patients import router as patients_router
from app.api.diagnoses import router as diagnoses_router
from app.api.flags import router as flags_router
from app.api.corrections import router as corrections_router
from app.api.notifications import router as notifications_router
from app.api.audit_logs import router as audit_router
from app.api.alerts import router as alerts_router
from app.services.alert_service import alert_service

logger = logging.getLogger("medrea.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info("Initializing database tables...")
    await init_db()
    yield
    logger.info("Application shutdown.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MEDREA Post-Diagnosis Reconciliation and Clinical Alert System",
    lifespan=lifespan,
)

# Enable CORS for frontend and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(patients_router, prefix=settings.API_V1_STR)
app.include_router(diagnoses_router, prefix=settings.API_V1_STR)
app.include_router(flags_router, prefix=settings.API_V1_STR)
app.include_router(corrections_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    """Identifies the application as MEDREA."""
    return {
        "app": settings.PROJECT_NAME,
        "description": "MEDREA Post-Diagnosis Reconciliation + Clinical Alert System",
        "version": settings.VERSION,
        "status": "online",
        "modules": [
            "M1_BackendCore",
            "M2_Database",
            "M3_Authentication",
            "M4_PatientHistory",
            "M5_DiagnosisIntake",
            "M8_FlagLifecycle",
            "M9_NotificationService",
            "M10_ESP32Pager",
            "M11_DoctorDashboard",
            "M12_PatientPortal",
            "M13_GuardianPortal",
            "M14_DisclosureConsent",
            "M15_AuditSystem",
        ]
    }


@app.get("/health")
def health_check():
    """Health status endpoint."""
    return {"status": "healthy"}


@app.websocket(settings.WS_PAGER_PATH)
async def websocket_pager_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for the physical ESP32 pager (and web dashboard live feeds).
    Maintains persistent duplex connection for alert dispatching and acknowledgment reception.
    """
    await alert_service.manager.connect_pager(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await alert_service.handle_incoming_client_message(data)
    except WebSocketDisconnect:
        alert_service.manager.disconnect_pager(websocket)
        logger.info("[WS] Pager client disconnected.")
    except Exception as e:
        logger.error(f"[WS] Unexpected WebSocket error: {e}")
        alert_service.manager.disconnect_pager(websocket)
