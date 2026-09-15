# MEDREA Operational Setup & Run Details (Living Document)

> [!IMPORTANT]
> **Operational Reference for Developers & AI Agents**:
> Before running, modifying, or testing any component that depends on local environment settings, hardware pinouts, or network configurations, read this document first.
> **DO NOT** commit actual passwords, private keys, API tokens, or personal Wi-Fi credentials into this file or any Git-tracked file. Document the variable name, destination file, and configuration instructions only.

---

## 1. Preserved Hardware Configuration

The following hardware pin mapping for the **ESP32 Dev Module + 128x64 SSD1306 SPI OLED** has been physically verified and must be preserved:

| OLED Display Pin | ESP32 GPIO Pin | Signal Name | Description |
|---|---|---|---|
| **GND** | GND | Ground | Power ground |
| **VCC** | 3.3V | VCC | 3.3V power rail |
| **D0** | GPIO 18 | `OLED_CLK` | SPI Clock |
| **D1** | GPIO 23 | `OLED_MOSI` | SPI Master-Out-Slave-In (Data) |
| **RES** | GPIO 4 | `OLED_RESET`| Display hardware reset |
| **DC** | GPIO 2 | `OLED_DC` | Data / Command control select |
| **CS** | GPIO 5 | `OLED_CS` | SPI Chip Select |

*Display Specs*: 128x64 monochrome OLED, SSD1306 driver, 4-wire SPI mode.

---

## 2. Required Local Configuration Files & Secrets

| Config File | Tracked in Git? | Template File | Purpose / Required Variables |
|---|---|---|---|
| `esp32/firmware/medrea_pager/config.h` | **NO** (in `.gitignore`) | `esp32/firmware/medrea_pager/config.h.example` | Local ESP32 parameters:<br>- `WIFI_SSID`: Local Wi-Fi network name<br>- `WIFI_PASSWORD`: Local Wi-Fi network password<br>- `BACKEND_HOST`: Local LAN IP of backend (e.g., `192.168.1.36`)<br>- `BACKEND_PORT`: `8000`<br>- `WS_PATH`: `"/ws/pager"` |
| `backend/medrea.db` | **NO** (in `.gitignore`) | Initialized by backend / seed script | Local SQLite database file for application state |
| `frontend/node_modules/` | **NO** (in `.gitignore`) | `package.json` | Installed frontend JavaScript dependencies |

---

## 3. Network, Ports & Routing

- **Backend Port**: `8000` (FastAPI REST APIs + WebSocket server at `/ws/pager`).
- **Frontend Port**: `5173` (Vite React development server with `/api` and `/ws` reverse proxy).
- **Physical ESP32 Connection**: Connects to `ws://<BACKEND_HOST>:8000/ws/pager`.
- **Local LAN Connectivity**: The ESP32 and the machine hosting FastAPI must be on the **same Wi-Fi subnet**. The ESP32 cannot connect to `localhost`.

---

## 4. Dependencies & Environments

### Backend (Python)
- **Python Version**: Python 3.10+ (tested on Python 3.14)
- **Virtual Environment**: Dedicated at `backend/.venv/`
- **Installed Packages**:
  - `fastapi>=0.115.0`
  - `uvicorn[standard]>=0.30.0`
  - `pydantic>=2.7.0`
  - `websockets>=12.0`
  - `sqlalchemy>=2.0.0`
  - `aiosqlite>=0.20.0`
  - `passlib[bcrypt]>=1.7.4`
  - `python-jose[cryptography]>=3.3.0`
  - `pytest>=8.0.0`
  - `httpx>=0.27.0`

### Frontend (React + Vite)
- **Runtime**: Node.js v18+ & npm
- **Installed Packages**:
  - `react`, `react-dom`
  - `vite`
  - `lucide-react` (clinical and system icons)

### ESP32 Firmware (Arduino IDE / PlatformIO)
- **Detected Chip**: `ESP32-D0WD-V3 (revision v3.1)` on `COM5`
- **Required Libraries**:
  1. `Adafruit SSD1306` (v2.5.17)
  2. `Adafruit GFX Library` (v1.12.6)
  3. `WebSockets` by Markus Sattler (v2.7.2)
  4. `ArduinoJson` by Benoît Blanchon (v7.4.3)

---

## 5. Pre-Seeded Clinical Accounts

To test the multi-role workflows immediately after seeding (`python backend/scripts/seed_demo_data.py`), the following deterministic test personas are provided:

| Persona Role | Login Email | Password | Identifier | Notes |
|---|---|---|---|---|
| **Clinician / Doctor** | `doctor@medrea.local` | `Doctor@123` | `D101` | Dr. Aditi Sharma (Attending physician, flag triage, diagnosis intake, correction reviewer) |
| **Patient** | `patient@medrea.local` | `Patient@123` | `P1042` | Rahul Verma (Documented Penicillin allergy, manages access requests, submits corrections) |
| **Legal Guardian** | `guardian@medrea.local` | `Guardian@123` | `G201` | Sunita Verma (Legal proxy for P1042, views withheld clinical notes under therapeutic privilege) |
| **Secondary Patient** | `patient2@medrea.local` | `Patient@123` | `P1091` | Secondary clinical evaluation record |

---

## 6. Startup & Execution Commands

### A. Seed Demo Database
```powershell
$env:PYTHONPATH="d:\MEDATHON\backend\.venv\Lib\site-packages;d:\MEDATHON\backend"
& "C:\users\dell\appdata\local\python\pythoncore-3.14-64\python.exe" d:\MEDATHON\backend\scripts\seed_demo_data.py
```

### B. Start FastAPI Backend (0.0.0.0:8000)
```powershell
$env:PYTHONPATH="d:\MEDATHON\backend\.venv\Lib\site-packages;d:\MEDATHON\backend"
& "C:\users\dell\appdata\local\python\pythoncore-3.14-64\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir d:\MEDATHON\backend
```

### C. Start Frontend Dev Server (Port 5173)
```powershell
cd d:\MEDATHON\frontend
npm run dev -- --host 0.0.0.0 --port 5173
```
Access in browser: `http://localhost:5173`

### D. Build Production Frontend Bundle
```powershell
cd d:\MEDATHON\frontend
npm run build
```

### E. Run Full Test Suite
```powershell
$env:PYTHONPATH="d:\MEDATHON\backend\.venv\Lib\site-packages;d:\MEDATHON\backend"
& "C:\users\dell\appdata\local\python\pythoncore-3.14-64\python.exe" -m pytest backend/tests/ -v
```

### F. Developer Wake-Up Utility
```powershell
$env:PYTHONPATH="d:\MEDATHON\backend\.venv\Lib\site-packages;d:\MEDATHON\backend"
& "C:\users\dell\appdata\local\python\pythoncore-3.14-64\python.exe" d:\MEDATHON\backend\scripts\wake_me.py
```
- Plays a distinctive 4-note ascending chime sequence across 3 cycles using `winsound.Beep`.
- Displays a Windows native `MessageBoxW` alert announcing completion of the autonomous software scope and that human review is required before starting the computational reasoning layer.

---

## 7. Change History

| Date | Author / Agent | Changes Made |
|---|---|---|
| 2026-09-15 | Antigravity AI | Initial document creation for Vertical Slice 1: Documented preserved SPI OLED pins, `config.h` requirements, Python venv commands, uvicorn LAN binding, ESP32 libraries, and automated test instructions. |
| 2026-09-15 | Antigravity AI | Physical Validation: Identified chip as `ESP32-D0WD-V3 (rev v3.1)` on `COM5`. Documented installed library versions (WebSockets 2.7.2, ArduinoJson 7.4.3), arduino-cli toolchain path, and Windows Firewall execution details for `0.0.0.0` binding. |
| 2026-09-15 | Antigravity AI | Autonomous Application Infrastructure & Frontend: Added SQLite database details (`medrea.db`), seed script instructions, pre-seeded clinical test credentials, Vite React setup and build commands, and documented the Windows wake-up utility (`backend/scripts/wake_me.py`). |
| 2026-09-15 | Antigravity AI | Comprehensive Frontend Functional Audit & Fix: Fixed Navbar prop mismatch (`onRoleChange`, `activeTab`, `onOpenAudit`), aligned persona names, fixed patient correction schema in frontend, corrected timeline and patient entity paths in Patient & Guardian portals, fixed AuditLogModal field mappings, and verified all 10 interactive workflows end-to-end against live backend and WebSocket stream. |
