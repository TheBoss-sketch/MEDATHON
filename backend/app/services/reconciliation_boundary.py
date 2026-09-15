"""Reconciliation Service Boundary.

==============================================================================
INTENTIONAL ARCHITECTURAL BOUNDARY:
This module defines the clean boundary and interface for the MEDREA
computational reconciliation & medical reasoning engine (Milestones M6/M7).

The actual NLP extraction, semantic graph contradiction detection, and LLM
reasoning provider adapters belong on the other side of this interface.

In this infrastructure milestone, `MockReconciliationPipeline` handles deterministic
test vectors (e.g. penicillin allergy vs amoxicillin) solely to validate data flow,
flag creation, database persistence, notifications, and ESP32 hardware delivery.
==============================================================================
"""

import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone

from app.models.patient import Patient
from app.models.diagnosis import Diagnosis
from app.models.flag import Flag

class ReconciliationResult:
    """Output contract produced by a reconciliation engine."""
    def __init__(
        self,
        has_flag: bool,
        severity: str = "LOW",  # LOW, MEDIUM, HIGH
        root_cause: str = "no_fault",  # doctor_gap, patient_gap, no_fault, intentional
        historical_reference: str = "",
        explanation: str = ""
    ):
        self.has_flag = has_flag
        self.severity = severity
        self.root_cause = root_cause
        self.historical_reference = historical_reference
        self.explanation = explanation

class ReconciliationEngineInterface(ABC):
    """Abstract interface to be implemented by the future M6/M7 computational reasoning engine."""

    @abstractmethod
    async def evaluate_reconciliation(
        self,
        new_diagnosis: Diagnosis,
        patient: Patient,
        prior_diagnoses: List[Diagnosis]
    ) -> List[ReconciliationResult]:
        """Evaluates clinical reconciliation between new clinical entry and patient history."""
        pass


class MockReconciliationPipeline(ReconciliationEngineInterface):
    """
    Deterministic test pipeline for infrastructure validation.
    DO NOT treat this as autonomous medical intelligence.
    It verifies data pipeline execution for known clinical test scenarios.
    """

    async def evaluate_reconciliation(
        self,
        new_diagnosis: Diagnosis,
        patient: Patient,
        prior_diagnoses: List[Diagnosis]
    ) -> List[ReconciliationResult]:
        results: List[ReconciliationResult] = []

        med_text = (new_diagnosis.medication or "").lower()
        note_text = new_diagnosis.clinical_note.lower()
        dx_text = new_diagnosis.diagnosis_name.lower()

        # Deterministic Test Scenario 1: Penicillin Allergy Conflict
        has_penicillin_allergy = any(
            "penicillin" in str(alg).lower() for alg in (patient.allergies or [])
        )
        prescribed_penicillin_derivative = any(
            drug in med_text or drug in note_text
            for drug in ["amoxicillin", "ampicillin", "augmentin", "penicillin"]
        )

        if has_penicillin_allergy and prescribed_penicillin_derivative:
            results.append(ReconciliationResult(
                has_flag=True,
                severity="HIGH",
                root_cause="doctor_gap",
                historical_reference="Documented patient allergy: Penicillin",
                explanation="Potential medication/allergy conflict: Patient has a documented Penicillin allergy, but a penicillin-class antibiotic was prescribed."
            ))

        # Deterministic Test Scenario 2: Explicit Test Triggers
        if "conflict" in note_text or "contradiction" in note_text:
            results.append(ReconciliationResult(
                has_flag=True,
                severity="HIGH",
                root_cause="doctor_gap",
                historical_reference="Historical medical record conflict test",
                explanation="Test vector: Clinical discrepancy flagged for doctor review."
            ))

        return results


# Active instance plugged into the application infrastructure
reconciliation_engine: ReconciliationEngineInterface = MockReconciliationPipeline()
