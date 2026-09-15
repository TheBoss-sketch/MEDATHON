"""Comprehensive automated test suite for MEDREA clinical application infrastructure."""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.session import AsyncSessionLocal, init_db
from app.services.alert_service import alert_service
from scripts.seed_demo_data import seed

@pytest.fixture(autouse=True)
async def prepare_clean_db():
    """Ensure database schema and demo seed are present for tests."""
    await init_db()
    await seed()
    alert_service.manager.active_pagers.clear()
    alert_service._ack_handlers.clear()
    yield
    alert_service.manager.active_pagers.clear()
    alert_service._ack_handlers.clear()

@pytest.mark.anyio
async def test_auth_registration_and_login():
    import uuid
    unique_email = f"test_doc_{uuid.uuid4().hex[:6]}@medrea.local"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register a doctor
        doc_reg = {
            "name": "Dr. Test Pulmonologist",
            "email": unique_email,
            "password": "Password123!",
            "role": "DOCTOR",
            "specialty": "Pulmonology",
            "hospital": "Apex Healthcare"
        }
        res = await client.post("/api/auth/register", json=doc_reg)
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert data["user"]["role"] == "DOCTOR"

        # 2. Login with valid credentials
        login_res = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "Password123!"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        # 3. Test /me
        me_res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == unique_email

@pytest.mark.anyio
async def test_access_request_and_patient_timeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login pre-seeded doctor
        doc_login = await client.post("/api/auth/login", json={
            "email": "doctor@medrea.local",
            "password": "Doctor@123"
        })
        assert doc_login.status_code == 200
        doc_token = doc_login.json()["access_token"]
        doc_headers = {"Authorization": f"Bearer {doc_token}"}

        # Login pre-seeded patient P1042
        pat_login = await client.post("/api/auth/login", json={
            "email": "patient@medrea.local",
            "password": "Patient@123"
        })
        assert pat_login.status_code == 200
        pat_token = pat_login.json()["access_token"]
        pat_headers = {"Authorization": f"Bearer {pat_token}"}

        # 1. Doctor views timeline for P1042 (already approved in seed)
        res = await client.get("/api/patients/P1042/timeline", headers=doc_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["has_full_access"] is True
        assert len(data["timeline"]) > 0

        # Verify penicillin allergy is present in timeline
        allergy_items = [t for t in data["timeline"] if t["type"] == "ALLERGY"]
        assert any("Penicillin" in a["title"] for a in allergy_items)

        # 2. Doctor requests access to P1091 (not pre-approved)
        ar_res = await client.post("/api/patients/access-requests", json={
            "patient_id": "P1091",
            "notes": "Consultation evaluation"
        }, headers=doc_headers)
        assert ar_res.status_code in [201, 400]

@pytest.mark.anyio
async def test_diagnosis_intake_triggers_high_reconciliation_flag():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login doctor
        doc_login = await client.post("/api/auth/login", json={
            "email": "doctor@medrea.local",
            "password": "Doctor@123"
        })
        assert doc_login.status_code == 200
        doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}"}

        # Prescribe Amoxicillin to Patient P1042 who has Penicillin allergy
        diag_payload = {
            "patient_id": "P1042",
            "diagnosis_name": "Acute Streptococcal Pharyngitis",
            "clinical_note": "Throat erythematous with purulent exudate. Prescribing broad-spectrum penicillin.",
            "medication": "Amoxicillin 500mg",
            "dosage": "TID x 7 days",
            "disclose_to_patient": True
        }
        dx_res = await client.post("/api/diagnoses", json=diag_payload, headers=doc_headers)
        assert dx_res.status_code == 201
        dx_data = dx_res.json()
        assert len(dx_data["generated_flags"]) > 0
        flag_id = dx_data["generated_flags"][0]

        # Verify flag exists and is HIGH priority
        flags_res = await client.get("/api/flags?patient_id=P1042", headers=doc_headers)
        assert flags_res.status_code == 200
        flags = flags_res.json()
        matching_flag = next((f for f in flags if f["id"] == flag_id), None)
        assert matching_flag is not None
        assert matching_flag["severity"] == "HIGH"
        assert matching_flag["root_cause"] == "doctor_gap"
        assert "Penicillin" in matching_flag["historical_reference"]

@pytest.mark.anyio
async def test_flag_lifecycle_review_resolve_dismiss():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login doctor
        doc_login = await client.post("/api/auth/login", json={
            "email": "doctor@medrea.local",
            "password": "Doctor@123"
        })
        assert doc_login.status_code == 200
        doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}"}

        # Get existing flags
        flags_res = await client.get("/api/flags", headers=doc_headers)
        flags = flags_res.json()
        assert len(flags) > 0
        target_flag = flags[0]
        flag_id = target_flag["id"]

        # 1. Mark under review
        rev_res = await client.post(f"/api/flags/{flag_id}/review", headers=doc_headers)
        assert rev_res.status_code == 200
        assert rev_res.json()["status"] == "UNDER_REVIEW"

        # 2. Resolve flag with clinical action note
        resolve_res = await client.post(f"/api/flags/{flag_id}/resolve", json={
            "resolution_note": "Replaced Amoxicillin with Azithromycin 500mg daily due to documented penicillin allergy."
        }, headers=doc_headers)
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == "RESOLVED"
        assert "Azithromycin" in resolve_res.json()["resolution_note"]

@pytest.mark.anyio
async def test_patient_correction_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login patient P1042
        pat_login = await client.post("/api/auth/login", json={
            "email": "patient@medrea.local",
            "password": "Patient@123"
        })
        assert pat_login.status_code == 200
        pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}

        # 1. Patient suggests correction
        corr_payload = {
            "entity_type": "MEDICATION",
            "current_value": "Salbutamol Inhaler 100mcg",
            "suggested_value": "Discontinued",
            "note": "Stopped using this inhaler 2 months ago as symptoms resolved."
        }
        res = await client.post("/api/corrections", json=corr_payload, headers=pat_headers)
        assert res.status_code == 201
        corr_id = res.json()["id"]

        # 2. Doctor logs in and reviews pending corrections
        doc_login = await client.post("/api/auth/login", json={
            "email": "doctor@medrea.local",
            "password": "Doctor@123"
        })
        assert doc_login.status_code == 200
        doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}"}

        corr_list = await client.get("/api/corrections", headers=doc_headers)
        assert corr_list.status_code == 200
        assert any(c["id"] == corr_id for c in corr_list.json())

        # 3. Doctor accepts correction
        accept_res = await client.post(f"/api/corrections/{corr_id}/accept", headers=doc_headers)
        assert accept_res.status_code == 200
        assert accept_res.json()["status"] == "ACCEPTED"

        # 4. Patient verifies notification received
        notif_res = await client.get("/api/notifications", headers=pat_headers)
        assert notif_res.status_code == 200
        notifs = notif_res.json()
        assert any(n["type"] == "CORRECTION_ACCEPTED" for n in notifs)

@pytest.mark.anyio
async def test_withheld_diagnosis_and_guardian_notification():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        doc_login = await client.post("/api/auth/login", json={
            "email": "doctor@medrea.local",
            "password": "Doctor@123"
        })
        assert doc_login.status_code == 200
        doc_headers = {"Authorization": f"Bearer {doc_login.json()['access_token']}"}

        # Log a diagnosis with therapeutic privilege (disclose_to_patient = False)
        withheld_payload = {
            "patient_id": "P1042",
            "diagnosis_name": "Suspicious Solitary Pulmonary Nodule",
            "clinical_note": "Incidental 1.8cm spicolated nodule right upper lobe on chest CT. Palliative staging pending biopsy.",
            "disclose_to_patient": False,
            "disclosure_reason": "Therapeutic privilege: Awaiting confirmatory pathology before disclosure to prevent severe acute distress.",
            "patient_facing_text": "Follow-up chest imaging recommended."
        }
        res = await client.post("/api/diagnoses", json=withheld_payload, headers=doc_headers)
        assert res.status_code == 201
        assert res.json()["guardian_notified"] is True

        # Guardian Sunita Verma logs in and checks notifications
        grd_login = await client.post("/api/auth/login", json={
            "email": "guardian@medrea.local",
            "password": "Guardian@123"
        })
        assert grd_login.status_code == 200
        grd_headers = {"Authorization": f"Bearer {grd_login.json()['access_token']}"}

        notif_res = await client.get("/api/notifications", headers=grd_headers)
        assert notif_res.status_code == 200
        notifs = notif_res.json()
        assert any(n["type"] == "WITHHELD_DIAGNOSIS" for n in notifs)
