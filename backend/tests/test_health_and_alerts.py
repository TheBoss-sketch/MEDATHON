"""Automated test suite for MEDREA Vertical Slice 1."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.alert_service import alert_service

@pytest.fixture(autouse=True)
def reset_service_state():
    """Ensure connections and handlers are clean between tests."""
    alert_service.manager.active_pagers.clear()
    alert_service._ack_handlers.clear()
    yield
    alert_service.manager.active_pagers.clear()
    alert_service._ack_handlers.clear()

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "MEDREA"
    assert data["status"] == "online"

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_trigger_alert_success():
    payload = {
        "type": "MEDREA_ALERT",
        "severity": "HIGH",
        "patient_id": "P1042",
        "message": "Potential medication conflict",
        "diagnosis": "Bacterial infection",
        "medication": "Amoxicillin"
    }
    response = client.post("/api/alerts/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "dispatched"
    assert data["alert"]["patient_id"] == "P1042"
    assert data["alert"]["severity"] == "HIGH"
    assert data["delivered_to_pagers"] == 0  # No pagers connected in this isolated test

def test_trigger_alert_invalid_severity():
    # Only LOW, MEDIUM, HIGH are allowed per project specification
    payload = {
        "type": "MEDREA_ALERT",
        "severity": "CRITICAL",
        "patient_id": "P1042",
        "message": "Unknown severity test"
    }
    response = client.post("/api/alerts/test", json=payload)
    assert response.status_code == 422  # Unprocessable Entity

def test_trigger_alert_missing_required_fields():
    payload = {
        "type": "MEDREA_ALERT",
        "severity": "HIGH"
        # missing patient_id and message
    }
    response = client.post("/api/alerts/test", json=payload)
    assert response.status_code == 422

def test_websocket_pager_end_to_end():
    """Tests WebSocket connection, alert delivery to connected pager, and client ack reception."""
    acks_received = []

    def on_ack(ack_packet):
        acks_received.append(ack_packet)

    alert_service.register_ack_handler(on_ack)

    # Connect mock ESP32 pager via WebSocket
    with client.websocket_connect("/ws/pager") as websocket:
        assert len(alert_service.manager.active_pagers) == 1

        # Trigger an alert via HTTP POST
        alert_payload = {
            "type": "MEDREA_ALERT",
            "severity": "HIGH",
            "patient_id": "P1042",
            "message": "Potential medication conflict",
            "diagnosis": "Bacterial infection",
            "medication": "Amoxicillin"
        }
        post_response = client.post("/api/alerts/test", json=alert_payload)
        assert post_response.status_code == 200
        assert post_response.json()["delivered_to_pagers"] == 1

        # Pager receives message frame over WebSocket
        received_raw = websocket.receive_text()
        received_json = json.loads(received_raw)
        assert received_json["type"] == "MEDREA_ALERT"
        assert received_json["patient_id"] == "P1042"
        assert received_json["severity"] == "HIGH"
        assert received_json["medication"] == "Amoxicillin"

        # Mock ESP32 sending an acknowledgment back
        ack_payload = {
            "type": "ALERT_ACK",
            "patient_id": "P1042",
            "status": "ACKNOWLEDGED",
            "device_ip": "192.168.1.150"
        }
        websocket.send_text(json.dumps(ack_payload))

    # After exiting context, pager is disconnected
    assert len(alert_service.manager.active_pagers) == 0
    assert len(acks_received) == 1
    assert acks_received[0].patient_id == "P1042"
    assert acks_received[0].status == "ACKNOWLEDGED"
