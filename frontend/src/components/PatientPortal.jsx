import React, { useState, useEffect } from "react";
import { getPatientRecord, listAccessRequests, respondAccessRequest, submitCorrection } from "../services/api";
import { User, ShieldCheck, Clock, FileText, Send, CheckCircle2, XCircle, AlertCircle } from "lucide-react";

export default function PatientPortal({ currentUser, user }) {
  const effectiveUser = currentUser || user;
  const [patientData, setPatientData] = useState(null);
  const [accessRequests, setAccessRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [correctionTarget, setCorrectionTarget] = useState(null);
  const [suggestedText, setSuggestedText] = useState("");
  const [submittingCorrection, setSubmittingCorrection] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  const fetchPortalData = async () => {
    try {
      setLoading(true);
      const targetId = effectiveUser?.patient_id || "P1042";
      const [recordRes, requestsRes] = await Promise.all([
        getPatientRecord(targetId),
        listAccessRequests()
      ]);
      setPatientData(recordRes);
      setAccessRequests(Array.isArray(requestsRes) ? requestsRes : []);
    } catch (err) {
      console.error("Failed to load patient portal data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortalData();
  }, [effectiveUser]);

  const handleAccessResponse = async (requestId, approved) => {
    try {
      await respondAccessRequest(requestId, approved);
      setFeedbackMessage({
        type: approved ? "success" : "warning",
        text: `Doctor access request ${approved ? "approved" : "denied"} successfully.`
      });
      fetchPortalData();
    } catch (err) {
      setFeedbackMessage({ type: "error", text: "Failed to update access request: " + (err.message || "") });
    }
  };

  const handleSendCorrection = async (e) => {
    e.preventDefault();
    if (!suggestedText.trim()) return;
    setSubmittingCorrection(true);
    try {
      const patientId = patientData?.patient?.id || effectiveUser?.patient_id || "P1042";
      await submitCorrection({
        patient_id: patientId,
        entity_type: correctionTarget?.entity_type || "MEDICATION",
        current_value: correctionTarget?.current_text || "Current recorded clinical entry",
        suggested_value: suggestedText.trim(),
        note: suggestedText.trim()
      });
      setFeedbackMessage({
        type: "success",
        text: "Correction suggestion submitted to your attending physician for clinical review."
      });
      setCorrectionTarget(null);
      setSuggestedText("");
      fetchPortalData();
    } catch (err) {
      setFeedbackMessage({ type: "error", text: "Failed to submit correction: " + (err.message || "") });
    } finally {
      setSubmittingCorrection(false);
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "4rem" }}>
        <p style={{ color: "var(--text-muted)" }}>Loading your verified health records...</p>
      </div>
    );
  }

  const patient = patientData?.patient;
  const timeline = patientData?.timeline || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Patient Header Card */}
      <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "8px", background: "var(--surface-hover)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <User size={24} color="var(--primary)" />
          </div>
          <div>
            <h2 style={{ fontSize: "1.25rem", margin: 0 }}>{patient?.name || effectiveUser?.full_name || "Rahul Verma"}</h2>
            <div style={{ display: "flex", gap: "1rem", color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.25rem" }}>
              <span>ID: <strong style={{ color: "var(--text-primary)" }}>{patient?.id || effectiveUser?.patient_id || "P1042"}</strong></span>
              <span>Age: {patient?.age || 38}</span>
              <span>Gender: {patient?.gender || "Male"}</span>
            </div>
            {/* Clinical Tags */}
            <div style={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
              {patient?.allergies?.map((alg, i) => (
                <span key={i} className="badge badge-high" style={{ fontSize: "11px" }}>Allergy: {alg}</span>
              ))}
              {patient?.conditions?.map((c, i) => (
                <span key={i} className="badge badge-medium" style={{ fontSize: "11px" }}>Condition: {c}</span>
              ))}
              {patient?.medications?.map((m, i) => (
                <span key={i} className="badge badge-low" style={{ fontSize: "11px" }}>Rx: {m}</span>
              ))}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <span className="badge badge-low" style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <ShieldCheck size={14} /> Medical Record Cleared
          </span>
        </div>
      </div>

      {feedbackMessage && (
        <div className={`card`} style={{ borderLeft: `4px solid ${feedbackMessage.type === "success" ? "var(--success)" : "var(--warning)"}`, padding: "0.85rem 1.25rem" }}>
          <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--text-primary)" }}>{feedbackMessage.text}</p>
        </div>
      )}

      {/* Access Requests from Clinicians */}
      {accessRequests.filter(r => r.status === "PENDING").length > 0 && (
        <div className="card" style={{ borderColor: "var(--warning)", background: "rgba(245, 158, 11, 0.05)" }}>
          <h3 style={{ fontSize: "1rem", color: "var(--warning)", marginTop: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <AlertCircle size={18} /> Pending Clinician Access Requests
          </h3>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            The following physicians have requested permission to access your medical timeline:
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginTop: "0.75rem" }}>
            {accessRequests.filter(r => r.status === "PENDING").map(req => (
              <div key={req.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.75rem", background: "var(--surface)", border: "1px solid var(--border-color)", borderRadius: "6px" }}>
                <div>
                  <strong>Doctor ID: {req.doctor_id}</strong>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Purpose: {req.reason || "Clinical evaluation and reconciliation"}</div>
                </div>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button className="btn btn-outline" style={{ color: "var(--danger)", borderColor: "var(--danger)" }} onClick={() => handleAccessResponse(req.id, false)}>
                    <XCircle size={14} style={{ marginRight: "0.25rem" }} /> Deny
                  </button>
                  <button className="btn btn-primary" onClick={() => handleAccessResponse(req.id, true)}>
                    <CheckCircle2 size={14} style={{ marginRight: "0.25rem" }} /> Grant Access
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline of Cleared Medical Records */}
      <div className="card">
        <h3 style={{ fontSize: "1.1rem", marginTop: 0, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Clock size={18} /> Verified Clinical Records & Timeline
        </h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
          Only validated and clinically cleared entries are visible. If you identify a discrepancy, you may submit a structured correction for physician review.
        </p>

        {timeline && timeline.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {timeline.map((record, index) => (
              <div key={index} style={{ border: "1px solid var(--border-color)", borderRadius: "8px", padding: "1rem", background: "var(--surface)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.5rem" }}>
                  <div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      {record.type || "DIAGNOSIS"} • {new Date(record.date || Date.now()).toLocaleDateString()}
                    </span>
                    <h4 style={{ margin: "0.25rem 0", fontSize: "1rem" }}>{record.title || "Clinical Observation"}</h4>
                  </div>
                  <button
                    className="btn btn-outline"
                    style={{ fontSize: "0.75rem", padding: "0.3rem 0.6rem" }}
                    onClick={() => setCorrectionTarget({
                      entity_type: record.type || "DIAGNOSIS",
                      entity_id: record.metadata?.diagnosis_id || `ITEM_${index}`,
                      current_text: record.description || record.title
                    })}
                  >
                    Suggest Correction
                  </button>
                </div>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: "1.4" }}>
                  {record.description}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)", border: "1px dashed var(--border-color)", borderRadius: "8px" }}>
            <FileText size={32} style={{ margin: "0 auto 0.5rem", opacity: 0.5 }} />
            <p style={{ margin: 0 }}>No cleared records currently available for patient view.</p>
          </div>
        )}
      </div>

      {/* Suggest Correction Modal */}
      {correctionTarget && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "1rem" }}>
          <div className="card" style={{ maxWidth: "540px", width: "100%" }}>
            <h3 style={{ marginTop: 0, fontSize: "1.1rem" }}>Suggest Medical Record Correction</h3>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
              Your proposed correction will be reviewed by the attending physician before any record is amended.
            </p>

            <form onSubmit={handleSendCorrection}>
              <div style={{ marginBottom: "1rem" }}>
                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.4rem" }}>
                  Current Record Text
                </label>
                <div style={{ background: "var(--surface-hover)", padding: "0.75rem", borderRadius: "6px", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
                  {correctionTarget.current_text}
                </div>

                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.4rem" }}>
                  Your Correction or Clarification *
                </label>
                <textarea
                  className="input-field"
                  rows={4}
                  required
                  placeholder="Describe the discrepancy (e.g. 'I do not tolerate Amoxicillin; I broke out in hives in 2021')."
                  value={suggestedText}
                  onChange={(e) => setSuggestedText(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
                <button type="button" className="btn btn-outline" onClick={() => setCorrectionTarget(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submittingCorrection}>
                  <Send size={14} style={{ marginRight: "0.4rem" }} />
                  {submittingCorrection ? "Submitting..." : "Submit for Physician Review"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
