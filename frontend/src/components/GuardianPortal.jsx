import React, { useState, useEffect } from "react";
import { getPatientRecord, listNotifications, markNotificationRead } from "../services/api";
import { Shield, Users, AlertTriangle, Clock, Eye, CheckCircle2 } from "lucide-react";

export default function GuardianPortal({ currentUser, user }) {
  const effectiveUser = currentUser || user;
  const [dependentData, setDependentData] = useState(null);
  const [caregiverNotifications, setCaregiverNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDiagnosis, setSelectedDiagnosis] = useState(null);

  const fetchGuardianData = async () => {
    try {
      setLoading(true);
      // Fetch dependent patient (e.g. P1042)
      const dependentId = effectiveUser?.dependent_id || "P1042";
      const [patientRes, notifsRes] = await Promise.all([
        getPatientRecord(dependentId),
        listNotifications()
      ]);
      setDependentData(patientRes);
      setCaregiverNotifications(Array.isArray(notifsRes) ? notifsRes : []);
    } catch (err) {
      console.error("Failed to load guardian portal data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGuardianData();
  }, [effectiveUser]);

  const handleDismissNotification = async (id) => {
    try {
      await markNotificationRead(id);
      setCaregiverNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch (err) {
      console.error("Failed to mark notification read", err);
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "4rem" }}>
        <p style={{ color: "var(--text-muted)" }}>Loading dependent health records & caregiver disclosures...</p>
      </div>
    );
  }

  const patient = dependentData?.patient;
  const timeline = dependentData?.timeline || [];

  // Find records that were withheld from patient (therapeutic privilege)
  const privilegedRecords = timeline.filter(r =>
    r.title?.includes("[Withheld from Patient]") ||
    r.description?.includes("Withholding reason:") ||
    r.metadata?.disclose_to_patient === false
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Guardian Header */}
      <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "8px", background: "rgba(59, 130, 246, 0.15)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Shield size={24} color="var(--primary)" />
          </div>
          <div>
            <h2 style={{ fontSize: "1.25rem", margin: 0 }}>Designated Legal Guardian Dashboard</h2>
            <div style={{ display: "flex", gap: "1rem", color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.25rem" }}>
              <span>Guardian: <strong style={{ color: "var(--text-primary)" }}>{effectiveUser?.full_name || "Sunita Verma"}</strong></span>
              <span>Dependent Ward: <strong style={{ color: "var(--text-primary)" }}>{patient?.name || "Rahul Verma"} ({patient?.id || "P1042"})</strong></span>
              <span>Relationship: Primary Power of Attorney / Guardian</span>
            </div>
          </div>
        </div>
        <span className="badge badge-medium" style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
          <Users size={14} /> Caregiver Proxy Active
        </span>
      </div>

      {/* Therapeutic Privilege Disclosures Banner */}
      {privilegedRecords.length > 0 && (
        <div className="card" style={{ borderColor: "var(--warning)", background: "rgba(245, 158, 11, 0.05)" }}>
          <h3 style={{ fontSize: "1.05rem", color: "var(--warning)", marginTop: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <AlertTriangle size={18} /> Therapeutic Privilege Disclosures ({privilegedRecords.length})
          </h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: "1.4" }}>
            The clinician has recorded findings withheld from the patient under therapeutic privilege to prevent severe acute distress. As the designated legal guardian, you are entrusted with these clinical findings.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "1rem" }}>
            {privilegedRecords.map((rec, idx) => (
              <div key={idx} style={{ background: "var(--surface)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "0.85rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <span className="badge badge-high" style={{ fontSize: "0.7rem", marginBottom: "0.25rem" }}>WITHHELD FROM PATIENT</span>
                    <h4 style={{ margin: "0.25rem 0", fontSize: "0.95rem" }}>{rec.title}</h4>
                  </div>
                  <button className="btn btn-outline" style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }} onClick={() => setSelectedDiagnosis(rec)}>
                    <Eye size={12} style={{ marginRight: "0.25rem" }} /> Full Clinical Note
                  </button>
                </div>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  {rec.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Caregiver Alerts & Notifications */}
      <div className="card">
        <h3 style={{ fontSize: "1.1rem", marginTop: 0, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Clock size={18} /> Urgent Reconciliation & Safety Alerts
        </h3>
        {caregiverNotifications.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {caregiverNotifications.map(notif => (
              <div key={notif.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.85rem", background: notif.read ? "var(--surface)" : "var(--surface-hover)", border: "1px solid var(--border-color)", borderRadius: "6px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span className="badge badge-medium">{notif.type || "ALERT"}</span>
                    <strong>{notif.title}</strong>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{new Date(notif.created_at || Date.now()).toLocaleTimeString()}</span>
                  </div>
                  <p style={{ margin: "0.25rem 0 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>{notif.message}</p>
                </div>
                {!notif.read && (
                  <button className="btn btn-outline" style={{ fontSize: "0.75rem", padding: "0.3rem 0.6rem" }} onClick={() => handleDismissNotification(notif.id)}>
                    <CheckCircle2 size={14} style={{ marginRight: "0.25rem" }} /> Acknowledge
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0 }}>No caregiver notifications recorded.</p>
        )}
      </div>

      {/* Full Patient Medical History */}
      <div className="card">
        <h3 style={{ fontSize: "1.1rem", marginTop: 0, marginBottom: "1rem" }}>
          Dependent Clinical History & Records ({timeline.length})
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {timeline.map((rec, idx) => (
            <div key={idx} style={{ padding: "0.85rem", border: "1px solid var(--border-color)", borderRadius: "6px", background: "var(--surface)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{rec.type || "RECORD"} • {new Date(rec.date || Date.now()).toLocaleDateString()}</span>
                {(rec.title?.includes("[Withheld from Patient]") || rec.metadata?.disclose_to_patient === false) && (
                  <span className="badge badge-medium" style={{ fontSize: "0.7rem" }}>Guardian-Only</span>
                )}
              </div>
              <h4 style={{ margin: "0.25rem 0", fontSize: "0.95rem" }}>{rec.title}</h4>
              <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)" }}>{rec.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Modal for Full Clinical Note */}
      {selectedDiagnosis && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "1rem" }}>
          <div className="card" style={{ maxWidth: "600px", width: "100%" }}>
            <h3 style={{ marginTop: 0 }}>{selectedDiagnosis.title}</h3>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Recorded: {new Date(selectedDiagnosis.date || Date.now()).toLocaleString()}
            </p>
            <div style={{ background: "var(--surface-hover)", padding: "1rem", borderRadius: "6px", margin: "1rem 0", fontSize: "0.9rem", lineHeight: "1.5" }}>
              {selectedDiagnosis.description}
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button className="btn btn-primary" onClick={() => setSelectedDiagnosis(null)}>
                Close Note
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
