# MEDREA: Clinical Reconciliation & Hardware Alert Platform

MEDREA is a clinical discrepancy reconciliation and decision-support platform designed to protect patients from clinical oversights, contraindications, and communication silos across complex hospital workflows.

The system pairs a multi-role clinical web command center (for Attending Doctors, Patients, and Legal Guardians) with dedicated hardware alert pagers (ESP32 microcontrollers driving SPI OLED displays) to deliver real-time, high-priority clinical warnings directly to clinicians.

---

## Architecture Overview

MEDREA is architected in decoupled, high-cohesion layers:

```
                      +-----------------------------+
                      |   Clinical Command Center   |
                      |    (React 18 + Vite SPA)    |
                      +--------------+--------------+
                                     |
               HTTP REST (/api)      |      WebSocket (/ws/pager)
                                     v
                      +-----------------------------+
                      |       FastAPI Backend       |
                      |   (Async Python 3.10+)      |
                      +--------------+--------------+
                                     |
         +---------------------------+---------------------------+
         |                           |                           |
         v                           v                           v
+------------------+     +------------------------+     +------------------+
|   SQLite Async   |     |  Reconciliation Engine |     |  ESP32 Hardware  |
|  (SQLAlchemy 2)  |     |   Interface Boundary   |     |   Alert Pagers   |
|   Database       |     | (Deterministic / M6-M7)|     | (SSD1306 SPI OLED|
+------------------+     +------------------------+     +------------------+
```

1. **Frontend (`frontend/`)**: React 18 SPA built with Vite. Implements role-gated clinical views:
   - **Doctor Command Center**: Diagnostic intake, real-time alert dispatch, priority triage queue for reconciliation flags, and patient correction review.
   - **Patient Portal**: Medical history timeline (filtered for therapeutic safety), doctor access authorization requests, and structured discrepancy reporting.
   - **Guardian Portal**: Legal proxy view for dependent wards, unredacted therapeutic privilege notes withheld from patients, and caregiver notifications.
   - **Compliance Audit Modal**: Real-time immutable record of all clinical events.
2. **Backend (`backend/app/`)**: High-performance asynchronous FastAPI service:
   - Role-Based Access Control (RBAC) with JWT Bearer authentication.
   - Domain models: Patients, Doctors, Guardians, Access Requests, Diagnoses, Flags, Corrections, Notifications, Audit Logs, and Alert Deliveries.
   - WebSocket Connection Manager (`/ws/pager`) broadcasting instant telemetry to hardware pagers and web listeners.
3. **Database (`medrea.db`)**: Local SQLite database via SQLAlchemy 2.0 async engine (`sqlite+aiosqlite`). Completely reproducible from synthetic seeds.
4. **Hardware Pager (`esp32/firmware/medrea_pager/`)**: Dedicated physical alert pager running on ESP32 with a 128x64 SSD1306 SPI OLED display. Connects via persistent auto-reconnecting WebSocket client.

---

## Current Implementation Status & Boundaries

### Completed Milestones
- **Hardware Integration**: Validated ESP32 Dev Module firmware with SPI OLED display rendering priority alerts in real time over local LAN WebSockets.
- **Data Persistence**: SQLAlchemy async schema with full domain models and audit logging.
- **Security & Roles**: Passlib/bcrypt password hashing, JWT token lifecycle, and role permission dependencies.
- **Clinical Workflows**: Multi-role patient access governance, diagnosis logging, priority flag triage, patient discrepancy correction submissions, guardian therapeutic privilege access, and system audit trails.
- **Frontend Layer**: 100% functional, responsive, role-switching clinical UI with live WebSocket alert banners and zero mock placeholders.

### Current Computational-Engine Boundary (Stopping Point)
- The application layer connects to the reconciliation system via the decoupled interface `IReconciliationEngine` ([backend/app/services/reconciliation_boundary.py](backend/app/services/reconciliation_boundary.py)).
- Currently, a **deterministic mock reconciliation engine** runs at this boundary. It evaluates diagnoses against patient allergy and condition profiles (e.g. flagging amoxicillin against penicillin allergies as a HIGH severity conflict) and triggers the alert pipeline.
- **Milestones M6 and M7 (Deep Learning / LLM Biomedical Reasoning Engine)** have intentionally not yet been implemented and will plug cleanly into this existing interface boundary without modifying frontend or database models.

---

## Teammate Setup Guide

### 1. Prerequisites
- **Python**: 3.10+ (tested on Python 3.10 - 3.14)
- **Node.js**: v18+ and npm
- **Git**: Installed and configured
- *(Optional for physical hardware)*: ESP32 board, 128x64 SSD1306 SPI OLED, and Arduino IDE 2.x

---

### 2. Backend Setup & Database Seeding

1. Navigate to the backend directory and create a virtual environment:
   ```bash
   cd backend
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Seed the database with synthetic development data:
   ```bash
   python scripts/seed_demo_data.py
   ```
   *This creates a local `medrea.db` populated with doctors, patients, guardians, access requests, diagnoses, flags, and audit events.*

---

### 3. Frontend Setup

1. In a separate terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Verify production build:
   ```bash
   npm run build
   ```

---

### 4. Running the Application Locally

1. **Start the FastAPI Backend** (Terminal 1, from project root or `backend/`):
   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - WebSocket Alert Stream: `ws://localhost:8000/ws/pager`

2. **Start the Vite Frontend** (Terminal 2, from `frontend/`):
   ```bash
   cd frontend
   npm run dev -- --host 0.0.0.0 --port 5173
   ```
   - Open your browser to [http://localhost:5173](http://localhost:5173)

---

### 5. Pre-Seeded Demo Accounts

Switch roles directly using the top navigation bar or log in with these seeded test accounts:

| Role | Email | Password | Persona / Details |
|---|---|---|---|
| **Clinician / Doctor** | `doctor@medrea.local` | `Doctor@123` | **Dr. Aditi Sharma** (Attending Physician, triage, diagnosis intake) |
| **Patient** | `patient@medrea.local` | `Patient@123` | **Rahul Verma** (Patient P1042, Penicillin allergy, access management) |
| **Legal Guardian** | `guardian@medrea.local` | `Guardian@123` | **Sunita Verma** (Legal Guardian for P1042, views withheld records) |

---

### 6. Hardware Alert Pager Setup (ESP32)

*If you have an ESP32 microcontroller and SSD1306 OLED display:*

1. Open `esp32/firmware/medrea_pager/README.md` for pinouts and library dependencies.
2. Copy the configuration template:
   ```bash
   cp esp32/firmware/medrea_pager/config.h.example esp32/firmware/medrea_pager/config.h
   ```
3. Edit `config.h`:
   - Set `WIFI_SSID` and `WIFI_PASSWORD` to your local Wi-Fi.
   - Set `BACKEND_HOST` to your computer's local LAN IP (e.g. `192.168.1.50`). **Do not use `localhost`**.
   - Set `BACKEND_PORT` to `8000`.
4. Flash `medrea_pager.ino` via Arduino IDE.
5. `config.h` is strictly excluded by `.gitignore` and must never be committed.

---

### 7. Running Automated Tests

Run the complete backend test suite:
```bash
pytest backend/tests/ -v
```

---

## Important Prototype Limitations

1. **Reconciliation Engine**: As noted above, M6/M7 advanced biomedical reasoning with external LLM adapters is decoupled and currently mocked with deterministic pattern rules.
2. **Local Wi-Fi Subnet**: The physical ESP32 pager requires the backend host machine to be reachable over the local Wi-Fi network (firewall port 8000 must allow inbound LAN traffic).
3. **Database State**: `medrea.db` is a local SQLite database excluded from version control. Run `python backend/scripts/seed_demo_data.py` at any time to re-generate clean synthetic data.
4. **Operational Details**: Refer to [project_details/RUN_DETAILS.md](project_details/RUN_DETAILS.md) and [project_details/PROJECT_STATUS.md](project_details/PROJECT_STATUS.md) for full operational history.
