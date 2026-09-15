# MEDREA Architecture - Clinical Infrastructure & Alert System

## Executive Summary
MEDREA is a clinical post-diagnosis reconciliation and alerting system. It provides an autonomous safety net against medical errors, omitted patient history, drug-allergy contraindications, and therapeutic discrepancies.

This architecture establishes the complete non-computational software infrastructure, database persistence, role-based workflows, physical ESP32 pager telemetry, and clinical web command center—decoupled cleanly from the future computational reconciliation engine.

---

## Architectural Topology

```text
+------------------------------------------------------------------------------------------------+
|                                    MEDREA Clinical Frontend                                    |
|                               (React + Vite - Port 5173)                                       |
|                                                                                                |
|   +-----------------------+     +------------------------+     +---------------------------+   |
|   | Doctor Command Center |     | Patient Portal (P1042) |     | Guardian Portal (G201)    |   |
|   | - Triage Queue (M8)   |     | - Verified Timeline    |     | - Caregiver Proxy         |   |
|   | - Diagnosis Intake(M5)|     | - Access Authorizations|     | - Therapeutic Disclosures |   |
|   | - Corrections Review  |     | - Suggest Corrections  |     | - Safety Alerts           |   |
|   +-----------------------+     +------------------------+     +---------------------------+   |
+------------------------------------------------------------------------------------------------+
                                              || REST & WebSocket (/ws/pager)
                                              \/
+------------------------------------------------------------------------------------------------+
|                                  FastAPI Backend (Port 8000)                                   |
|                                                                                                |
|  +--------------------+   +---------------------+   +---------------------+   +-------------+  |
|  | Authentication &   |   | Patient & Timeline  |   | Flag Lifecycle &    |   | Compliance  |  |
|  | RBAC (/api/auth)   |   | Service (/patients) |   | Triage (/api/flags) |   | Audit Logs  |  |
|  +--------------------+   +---------------------+   +---------------------+   +-------------+  |
|                                      ||                                                        |
|                                      \/                                                        |
|  +------------------------------------------------------------------------------------------+  |
|  |                       Diagnosis Intake & Reconciliation Service Boundary                 |  |
|  |                          - IReconciliationEngine (Service Interface)                    |  |
|  |                          - MockDeterministicReconciliationEngine                         |  |
|  |                          [STOPPING BOUNDARY: Cleanly abstracts M6 / M7]                  |  |
|  +------------------------------------------------------------------------------------------+  |
|                  ||                                                     ||                     |
|                  \/                                                     \/                     |
|  +---------------------------------+                  +-------------------------------------+  |
|  | Database Layer (SQLAlchemy 2.0) |                  | Alert Service & ConnectionManager   |  |
|  | - SQLite (medrea.db)            |                  | - Broadcasts HIGH severity to pagers|  |
|  | - Complete clinical models      |                  | - Bidirectional WebSockets          |  |
|  +---------------------------------+                  +-------------------------------------+  |
+-------------------------------------------------------------------------||---------------------+
                                                                          ||
                                                                          \/ WebSocket (/ws/pager)
                                                                 +-------------------+
                                                                 | ESP32 Dev Module  |
                                                                 | (Silicon Labs CP) |
                                                                 +-------------------+
                                                                          || SPI
                                                                          \/
                                                                 +-------------------+
                                                                 | SSD1306 SPI OLED  |
                                                                 | 128x64 Displayer  |
                                                                 +-------------------+
```

---

## Modularity & Component Boundaries

### 1. The Computational Reconciliation Boundary (`backend/app/services/reconciliation_boundary.py`)
To prevent ad-hoc hardcoding while providing end-to-end functionality, the reasoning engine is decoupled behind the `IReconciliationEngine` interface:
```python
class IReconciliationEngine(ABC):
    @abstractmethod
    async def reconcile_diagnosis(
        self,
        new_diagnosis: Diagnosis,
        patient_history: List[Any],
        doctor_notes: Optional[str] = None
    ) -> List[FlagCreate]:
        pass
```
- **Current Implementation**: `MockDeterministicReconciliationEngine` performs deterministic rule-checking (e.g. penicillin allergy vs amoxicillin) to exercise flags and alerts.
- **Future M6/M7 Engine**: Will plug in directly without altering API contracts, database models, frontend interfaces, or alert routing.

### 2. Physical Alert & Telemetry Hub (`backend/app/services/alert_service.py`)
- Maintains active WebSocket connections to ESP32 pagers and frontend dashboards.
- Filters and broadcasts high-priority clinical flags instantly (`HIGH` severity).
- Collects device acknowledgments (`ALERT_ACK`).

### 3. Identity & Role-Based Access Control (`backend/app/core/security.py`, `backend/app/api/deps.py`)
- Token-based authentication (JWT with HMAC-SHA256).
- Strict role verification:
  - `DOCTOR`: Diagnosis intake, access requesting, flag triage, correction review.
  - `PATIENT`: Verified timeline inspection, doctor access authorization, correction submissions.
  - `GUARDIAN`: Caregiver proxy, therapeutic privilege inspection, emergency alert reception.
  - `ADMIN`: Global audit trail inspection and user management.

### 4. Therapeutic Privilege Gating (`backend/app/api/patients.py`, `backend/app/api/diagnoses.py`)
- Diagnoses flagged with `disclose_to_patient = False` are automatically redacted from patient-facing views to protect vulnerable individuals from immediate psychiatric/clinical trauma.
- Disclosures are routed directly to the patient's verified legal guardian.

### 5. Clinical Frontend Application (`frontend/`)
- Built with React and Vite.
- Styled using a dedicated CSS design system (`index.css`) prioritizing clinical contrast, information density, and rapid flag triage over generic SaaS aesthetics.
- Real-time WebSocket connection to `/ws/pager` displays active alerts synchronously with the physical ESP32 OLED.

---

## Data Schema & Storage Architecture

The persistence layer (`backend/app/models/`) is managed by SQLAlchemy 2.0 with asynchronous SQLite (`sqlite+aiosqlite:///./medrea.db`):

1. `users`: Authentication credentials, roles, email, active status.
2. `patients`: Demographic profile, blood group, allergies, guardian associations.
3. `doctors`: Medical license number, department, hospital affiliation.
4. `guardians`: Caregiver profiles, contact info, patient ward links.
5. `access_requests`: Clinician-to-patient record access requests and status (`PENDING`, `APPROVED`, `DENIED`).
6. `diagnoses`: Clinical encounter records, symptoms, medications, therapeutic disclosure flags.
7. `flags`: Reconciliation issues (`CONTRADICTION`, `OMISSION`, `CONTRAINDICATION`, `DOSAGE_ERROR`), severity (`LOW`, `MEDIUM`, `HIGH`), status (`OPEN`, `UNDER_REVIEW`, `RESOLVED`, `DISMISSED`), resolution notes.
8. `corrections`: Discrepancies reported by patients, status (`PENDING`, `ACCEPTED`, `DISMISSED`).
9. `notifications`: In-app clinical alerts for doctors, patients, and guardians.
10. `audit_logs`: Immutable clinical action trail for HIPAA/compliance tracking.
11. `alert_deliveries`: Telemetry logs of alerts dispatched to physical hardware pagers.

---

## Future Integration Guide: Computational Reconciliation Layer
The future computational engine will implement `IReconciliationEngine`:
1. Receive `new_diagnosis` and complete `patient_history`.
2. Execute biomedical NER and entity resolution.
3. Perform semantic comparison against medical knowledge bases or LLM clinical inference models.
4. Return a structured collection of `FlagCreate` objects with calculated severity and root cause reasoning.
5. Zero changes required to API endpoints, database schemas, frontend, or hardware pagers.
