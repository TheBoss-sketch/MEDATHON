import React, { useState, useEffect } from "react";
import Navbar from "./components/Navbar";
import DoctorCommandCenter from "./components/DoctorCommandCenter";
import PatientPortal from "./components/PatientPortal";
import GuardianPortal from "./components/GuardianPortal";
import AuditLogModal from "./components/AuditLogModal";
import { loginUser } from "./services/api";
import { AlertCircle, Wifi, Radio, Bell } from "lucide-react";

// Pre-seeded clinical test personas
const CLINICAL_ROLES = {
  DOCTOR: {
    email: "doctor@medrea.local",
    password: "Doctor@123",
    role: "DOCTOR",
    full_name: "Dr. Aditi Sharma",
    doctor_id: "D101"
  },
  PATIENT: {
    email: "patient@medrea.local",
    password: "Patient@123",
    role: "PATIENT",
    full_name: "Rahul Verma",
    patient_id: "P1042"
  },
  GUARDIAN: {
    email: "guardian@medrea.local",
    password: "Guardian@123",
    role: "GUARDIAN",
    full_name: "Sunita Verma",
    guardian_id: "G201",
    dependent_id: "P1042"
  }
};

export default function App() {
  const [currentRoleKey, setCurrentRoleKey] = useState("DOCTOR");
  const [currentUser, setCurrentUser] = useState(CLINICAL_ROLES.DOCTOR);
  const [activeTab, setActiveTab] = useState("doctor");
  const [auditOpen, setAuditOpen] = useState(false);
  const [liveAlert, setLiveAlert] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Authenticate whenever role switcher changes
  useEffect(() => {
    const authenticateRole = async () => {
      const persona = CLINICAL_ROLES[currentRoleKey];
      try {
        const tokenData = await loginUser(persona.email, persona.password);
        setCurrentUser({
          ...persona,
          name: tokenData.user?.name || persona.full_name,
          full_name: tokenData.user?.name || persona.full_name,
          token: tokenData.access_token
        });
      } catch (err) {
        console.warn("Could not login persona, proceeding with cached credentials", err);
        setCurrentUser(persona);
      }
    };
    authenticateRole();
  }, [currentRoleKey]);

  // Establish Live WebSocket to Backend Pager Stream (/ws/pager)
  useEffect(() => {
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws/pager`;

    let ws;
    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
        console.log("[MEDREA WS] Connected to pager alert stream.");
      };

      ws.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data);
          console.log("[MEDREA WS] Received alert packet:", payload);
          if (payload.type === "MEDREA_ALERT" || payload.event === "HIGH_SEVERITY_FLAG") {
            setLiveAlert(payload);
            // Auto-clear banner after 12 seconds
            setTimeout(() => setLiveAlert(null), 12000);
          }
        } catch (e) {
          console.error("[MEDREA WS] Failed to parse message:", e);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
      };

      ws.onerror = (err) => {
        setWsConnected(false);
      };
    } catch (e) {
      console.warn("WebSocket initialization failed:", e);
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const handleRoleChange = (roleKey) => {
    setCurrentRoleKey(roleKey);
    if (roleKey === "DOCTOR") setActiveTab("doctor");
    if (roleKey === "PATIENT") setActiveTab("patient");
    if (roleKey === "GUARDIAN") setActiveTab("guardian");
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Top Clinical Navigation Bar */}
      <Navbar
        currentUser={currentUser}
        currentRole={currentRoleKey}
        onRoleChange={handleRoleChange}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenAudit={() => setAuditOpen(true)}
      />

      {/* Live Physical Pager & System Status Sub-bar */}
      <div style={{ background: "var(--surface)", borderBottom: "1px solid var(--border-color)", padding: "0.4rem 2rem", fontSize: "0.8rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", color: "var(--text-muted)" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Radio size={14} color={wsConnected ? "var(--success)" : "var(--text-muted)"} />
            ESP32 Pager Broadcast: <strong style={{ color: wsConnected ? "var(--success)" : "var(--text-muted)" }}>{wsConnected ? "STREAM ACTIVE" : "STANDBY"}</strong>
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <Wifi size={14} color="var(--primary)" />
            Local Backend: <strong>http://127.0.0.1:8000</strong>
          </span>
        </div>
        <div style={{ color: "var(--text-muted)" }}>
          Target Architecture: <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>Non-Computational Reconciliation Baseline</span>
        </div>
      </div>

      {/* Real-time High Severity Alert Banner (Synchronized with ESP32 OLED Display) */}
      {liveAlert && (
        <div style={{ background: "rgba(239, 68, 68, 0.15)", borderBottom: "2px solid var(--danger)", padding: "0.85rem 2rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div style={{ background: "var(--danger)", color: "#fff", borderRadius: "4px", padding: "0.2rem 0.5rem", fontWeight: "bold", fontSize: "0.75rem" }}>
              CRITICAL HARDWARE PAGER BROADCAST
            </div>
            <div>
              <strong style={{ color: "var(--text-primary)" }}>{liveAlert.title || "HIGH SEVERITY RECONCILIATION FLAG"}</strong>
              <span style={{ marginLeft: "0.75rem", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                Patient {liveAlert.patient_id || liveAlert.patient}: {liveAlert.message || liveAlert.flag_type}
              </span>
            </div>
          </div>
          <button className="btn btn-outline" style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }} onClick={() => setLiveAlert(null)}>
            Dismiss Banner
          </button>
        </div>
      )}

      {/* Main Clinical Viewport */}
      <main className="container" style={{ flex: 1, padding: "2rem 1.5rem" }}>
        {activeTab === "doctor" && (
          <DoctorCommandCenter
            currentUser={currentUser}
            user={currentUser}
            onOpenAudit={() => setAuditOpen(true)}
          />
        )}
        {activeTab === "patient" && (
          <PatientPortal
            currentUser={currentUser}
            user={currentUser}
          />
        )}
        {activeTab === "guardian" && (
          <GuardianPortal
            currentUser={currentUser}
            user={currentUser}
          />
        )}
      </main>

      {/* Compliance Audit Modal */}
      <AuditLogModal isOpen={auditOpen} onClose={() => setAuditOpen(false)} />

      {/* Serious Clinical Footer */}
      <footer style={{ borderTop: "1px solid var(--border-color)", padding: "1rem 2rem", textAlign: "center", fontSize: "0.8rem", color: "var(--text-muted)", background: "var(--surface)" }}>
        MEDREA Clinical Post-Diagnosis Reconciliation System • Confidential Clinical Environment • Autonomous Software Baseline
      </footer>
    </div>
  );
}
