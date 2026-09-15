"""CLI tool to manually trigger test alerts to the MEDREA backend."""
import sys
import json
import urllib.request
import urllib.error

DEFAULT_URL = "http://127.0.0.1:8000/api/alerts/test"

SAMPLE_ALERT = {
    "type": "MEDREA_ALERT",
    "severity": "HIGH",
    "patient_id": "P1042",
    "message": "Potential medication conflict",
    "diagnosis": "Bacterial infection",
    "medication": "Amoxicillin"
}

def trigger_alert(url: str = DEFAULT_URL, alert_data: dict = None):
    payload = alert_data or SAMPLE_ALERT
    req_body = json.dumps(payload).encode("utf-8")
    
    print(f"Dispatching test alert to: {url}")
    print(f"Payload:\n{json.dumps(payload, indent=2)}")
    
    req = urllib.request.Request(
        url,
        data=req_body,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.getcode()
            resp_body = resp.read().decode("utf-8")
            print(f"\nResponse [{status_code}]:")
            print(json.dumps(json.loads(resp_body), indent=2))
            print("\n>> Alert successfully processed by backend!")
    except urllib.error.URLError as e:
        print(f"\n[ERROR] Failed to reach backend: {e}")
        print("Ensure the FastAPI server is running on http://localhost:8000")
        sys.exit(1)

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    trigger_alert(target_url)
