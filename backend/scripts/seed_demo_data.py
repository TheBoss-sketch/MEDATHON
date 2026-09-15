"""Seeds realistic clinical demo data into the MEDREA database."""
import asyncio
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal, init_db
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.guardian import Guardian
from app.models.access_request import AccessRequest
from app.models.diagnosis import Diagnosis
from app.models.flag import Flag
from app.models.audit_log import AuditLog
from app.core.security import hash_password

async def seed():
    print("Initializing database tables...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        existing = await db.execute(select(User).where(User.email == "doctor@medrea.local"))
        if existing.scalar_one_or_none():
            print("Demo data already seeded. Skipping.")
            return

        print("Seeding clinical users and profiles...")

        # 1. Doctor: Dr. Aditi Sharma
        doc_user = User(
            id="U_DOC_01",
            name="Dr. Aditi Sharma",
            email="doctor@medrea.local",
            password_hash=hash_password("Doctor@123"),
            role="DOCTOR",
            is_active=True,
        )
        db.add(doc_user)

        doctor = Doctor(
            id="D101",
            user_id="U_DOC_01",
            specialty="Pulmonology & Critical Care",
            hospital="Metro Apex Hospital",
            qualifications="MBBS, MD, FCCP",
            pager_device_id="ESP32_PAGER_01"
        )
        db.add(doctor)

        # 2. Patient: Rahul Verma (P1042) - Has Penicillin Allergy
        pat_user = User(
            id="U_PAT_01",
            name="Rahul Verma",
            email="patient@medrea.local",
            password_hash=hash_password("Patient@123"),
            role="PATIENT",
            is_active=True,
        )
        db.add(pat_user)

        patient = Patient(
            id="P1042",
            user_id="U_PAT_01",
            age=38,
            gender="Male",
            conditions=["Bronchial Asthma"],
            medications=["Salbutamol Inhaler 100mcg"],
            allergies=["Penicillin"],
        )
        db.add(patient)

        # 3. Guardian: Sunita Verma (Spouse of P1042)
        guard_user = User(
            id="U_GRD_01",
            name="Sunita Verma",
            email="guardian@medrea.local",
            password_hash=hash_password("Guardian@123"),
            role="GUARDIAN",
            is_active=True,
        )
        db.add(guard_user)

        guardian = Guardian(
            id="G201",
            user_id="U_GRD_01",
            linked_patient_id="P1042",
            relationship="Spouse & Caregiver"
        )
        db.add(guardian)

        # 4. Pre-approved Access Request for Doctor -> Patient P1042
        access_req = AccessRequest(
            id="AR1042",
            doctor_id="D101",
            patient_id="P1042",
            status="APPROVED",
            notes="Ongoing pulmonary and allergy monitoring"
        )
        db.add(access_req)

        # 5. Historical Diagnosis for P1042
        hist_dx = Diagnosis(
            id="DX1001",
            patient_id="P1042",
            doctor_id="D101",
            diagnosis_name="Acute Asthma Exacerbation",
            clinical_note="Patient presented with expiratory wheezing. Responded to nebulization.",
            medication="Salbutamol Inhaler",
            dosage="2 puffs PRN",
            disclose_to_patient=True,
            patient_facing_text="Mild asthma flare-up managed with inhaler.",
            guardian_notified=False,
        )
        db.add(hist_dx)

        # 6. Second Patient: Priya Nair (P1091)
        pat2_user = User(
            id="U_PAT_02",
            name="Priya Nair",
            email="patient2@medrea.local",
            password_hash=hash_password("Patient@123"),
            role="PATIENT",
            is_active=True,
        )
        db.add(pat2_user)

        patient2 = Patient(
            id="P1091",
            user_id="U_PAT_02",
            age=54,
            gender="Female",
            conditions=["Essential Hypertension"],
            medications=["Amlodipine 5mg"],
            allergies=["Sulfa drugs"],
        )
        db.add(patient2)

        # 7. Pre-existing Demo Flag for P1091
        demo_dx2 = Diagnosis(
            id="DX1002",
            patient_id="P1091",
            doctor_id="D101",
            diagnosis_name="Mild Fluid Retention",
            clinical_note="Observation for lower extremity edema; review anti-hypertensive regimen.",
            medication="Hydrochlorothiazide 12.5mg",
            dosage="Once daily",
            disclose_to_patient=True,
            patient_facing_text="Mild swelling being evaluated with medication adjustment.",
            guardian_notified=False,
        )
        db.add(demo_dx2)

        demo_flag = Flag(
            id="F201",
            patient_id="P1091",
            diagnosis_id="DX1002",
            historical_reference="Documented Sulfa allergy in record",
            root_cause="doctor_gap",
            severity="MEDIUM",
            status="OPEN",
            explanation="Hydrochlorothiazide contains sulfonamide moiety; potential cross-reactivity with documented Sulfa allergy.",
        )
        db.add(demo_flag)

        # Audit initial seed
        audit = AuditLog(
            id="AUD_SEED_01",
            actor_id="SYSTEM",
            actor_role="ADMIN",
            action="SYSTEM_INITIALIZED",
            target_type="DATABASE",
            target_id="medrea.db",
            details="Standard clinical demo dataset seeded successfully",
        )
        db.add(audit)

        await db.commit()
        print("Demo data seeded successfully!")
        print("\nCreated Test Accounts:")
        print("  Doctor:   doctor@medrea.local   / Doctor@123   (ID: D101)")
        print("  Patient:  patient@medrea.local  / Patient@123  (ID: P1042, Penicillin Allergy)")
        print("  Guardian: guardian@medrea.local / Guardian@123 (ID: G201, linked to P1042)")
        print("  Patient2: patient2@medrea.local / Patient@123  (ID: P1091)")

if __name__ == "__main__":
    asyncio.run(seed())
