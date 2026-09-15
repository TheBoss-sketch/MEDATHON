import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  User,
  PlusCircle,
  Radio,
  Eye,
  Check,
  X,
  History,
  Send,
  HelpCircle
} from 'lucide-react';
import { api } from '../services/api';

export default function DoctorCommandCenter({ currentUser, user, onOpenAudit }) {
  const effectiveUser = currentUser || user;
  const [stats, setStats] = useState({
    total_active: 0,
    high_priority: 0,
    medium_priority: 0,
    low_priority: 0,
    under_review: 0,
    resolved_today: 0,
  });
  const [flags, setFlags] = useState([]);
  const [corrections, setCorrections] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modals & Panels
  const [showDiagnosisModal, setShowDiagnosisModal] = useState(false);
  const [showResolveModal, setShowResolveModal] = useState(null); // Flag object
  const [showDismissModal, setShowDismissModal] = useState(null); // Flag object
  const [timelinePatient, setTimelinePatient] = useState(null); // Patient ID
  const [patientTimeline, setPatientTimeline] = useState(null);

  // Diagnosis Form State
  const [diagForm, setDiagForm] = useState({
    patient_id: 'P1042',
    diagnosis_name: 'Bacterial Throat Infection',
    clinical_note: 'Patient presents with severe sore throat, fever, and pharyngeal exudate.',
    medication: 'Amoxicillin 500mg',
    dosage: 'TID x 7 days',
    disclose_to_patient: true,
    disclosure_reason: '',
    patient_facing_text: 'Mild bacterial throat infection treatable with oral antibiotics.',
  });
  const [diagSubmitting, setDiagSubmitting] = useState(false);

  // Resolution note state
  const [resolutionNote, setResolutionNote] = useState('');
  const [dismissalReason, setDismissalReason] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, flagsData, corrsData, patsData] = await Promise.all([
        api.getFlagStats(),
        api.listFlags(),
        api.listCorrections(),
        api.listPatients(),
      ]);
      setStats(statsData);
      setFlags(flagsData);
      setCorrections(corrsData);
      setPatients(patsData);
    } catch (err) {
      console.error('Failed to load doctor dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 10000);
    return () => clearInterval(timer);
  }, []);

  const handleStartReview = async (flagId) => {
    try {
      await api.reviewFlag(flagId);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleResolveFlag = async () => {
    if (!resolutionNote || resolutionNote.trim().length < 5) {
      alert('Please provide a clinical resolution note (minimum 5 characters).');
      return;
    }
    try {
      await api.resolveFlag(showResolveModal.id, resolutionNote);
      setShowResolveModal(null);
      setResolutionNote('');
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDismissFlag = async () => {
    if (!dismissalReason || dismissalReason.trim().length < 5) {
      alert('Please provide a clinical justification for dismissing this flag.');
      return;
    }
    try {
      await api.dismissFlag(showDismissModal.id, dismissalReason);
      setShowDismissModal(null);
      setDismissalReason('');
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleOpenTimeline = async (patientId) => {
    try {
      const data = await api.getTimeline(patientId);
      setTimelinePatient(patientId);
      setPatientTimeline(data);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleAcceptCorrection = async (corrId) => {
    try {
      await api.acceptCorrection(corrId);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDismissCorrection = async (corrId) => {
    const reason = prompt('Please enter clinical reason for dismissing this correction suggestion:');
    if (!reason) return;
    try {
      await api.dismissCorrection(corrId, reason);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleSubmitDiagnosis = async (e) => {
    e.preventDefault();
    try {
      setDiagSubmitting(true);
      const res = await api.createDiagnosis(diagForm);
      setShowDiagnosisModal(false);
      loadData();

      if (res.generated_flags && res.generated_flags.length > 0) {
        alert(
          `Diagnosis intake saved! MEDREA generated ${res.generated_flags.length} reconciliation flag(s) and dispatched an alert to your physical ESP32 pager.`
        );
      } else {
        alert('Diagnosis intake saved successfully. No contradictions detected.');
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setDiagSubmitting(false);
    }
  };

  const handleTriggerHardwareAlert = async () => {
    try {
      const testAlert = {
        type: 'MEDREA_ALERT',
        severity: 'HIGH',
        patient_id: 'P1042',
        message: 'Potential medication conflict',
        diagnosis: 'Bacterial infection',
        medication: 'Amoxicillin',
      };
      await api.triggerTestAlert(testAlert);
      alert('High priority test alert dispatched to ESP32 physical pager!');
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px 20px' }}>
      {/* Top Header & Fast Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '4px' }}>
            Clinical Reconciliation Dashboard
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Active oversight of post-diagnosis contradictions, therapeutic non-disclosures, and medical history gaps.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={() => setShowDiagnosisModal(true)} className="btn btn-primary">
            <PlusCircle size={15} />
            Log New Diagnosis
          </button>
          <button onClick={handleTriggerHardwareAlert} className="btn btn-danger">
            <Radio size={15} />
            Test Pager Broadcast
          </button>
          <button onClick={onOpenAudit} className="btn btn-secondary">
            <History size={15} />
            Audit Trail
          </button>
        </div>
      </div>

      {/* Summary Stat Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '24px' }}>
        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderLeft: '4px solid var(--high-red)',
          borderRadius: 'var(--radius-sm)',
          padding: '14px 16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--high-red)' }}>HIGH PRIORITY</span>
            <AlertTriangle size={16} color="var(--high-red)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
            {stats.high_priority}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Immediate clinical conflict</div>
        </div>

        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderLeft: '4px solid var(--med-amber)',
          borderRadius: 'var(--radius-sm)',
          padding: '14px 16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--med-amber)' }}>MEDIUM PRIORITY</span>
            <Clock size={16} color="var(--med-amber)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
            {stats.medium_priority}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>History & dosage discrepancies</div>
        </div>

        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderLeft: '4px solid var(--low-cyan)',
          borderRadius: 'var(--radius-sm)',
          padding: '14px 16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--low-cyan)' }}>LOW PRIORITY</span>
            <CheckCircle size={16} color="var(--low-cyan)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
            {stats.low_priority}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Minor documentation notes</div>
        </div>

        <div style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderLeft: '4px solid var(--success-green)',
          borderRadius: 'var(--radius-sm)',
          padding: '14px 16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--success-green)' }}>RESOLVED FLAGS</span>
            <CheckCircle size={16} color="var(--success-green)" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: '700', fontFamily: 'var(--font-mono)' }}>
            {stats.resolved_today}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Actioned clinical reconciliations</div>
        </div>
      </div>

      {/* Main Reconciliation Triage Table */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-md)',
        marginBottom: '28px',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--border-default)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>
            Reconciliation Flags Queue (Priority Ordered)
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Showing {flags.length} flags
          </div>
        </div>

        {flags.length === 0 ? (
          <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            No active flags — all reviewed patient records are currently consistent.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--bg-surface-elevated)', borderBottom: '1px solid var(--border-default)' }}>
                  <th style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--text-secondary)' }}>Priority</th>
                  <th style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--text-secondary)' }}>Patient</th>
                  <th style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--text-secondary)' }}>Contradiction / Conflict</th>
                  <th style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--text-secondary)' }}>Root-Cause Attribution</th>
                  <th style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--text-secondary)' }}>Status</th>
                  <th style={{ padding: '10px 14px', fontWeight: '600', color: 'var(--text-secondary)', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {flags.map((flag) => {
                  const isHigh = flag.severity === 'HIGH';
                  const isMed = flag.severity === 'MEDIUM';
                  const isResolved = flag.status === 'RESOLVED';
                  const isDismissed = flag.status === 'DISMISSED';

                  return (
                    <tr
                      key={flag.id}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        background: isHigh && flag.status === 'OPEN' ? 'rgba(239, 68, 68, 0.04)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '12px 14px' }}>
                        <span className={`badge ${isHigh ? 'badge-high' : isMed ? 'badge-medium' : 'badge-low'}`}>
                          {flag.severity}
                        </span>
                      </td>

                      <td style={{ padding: '12px 14px' }}>
                        <div style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                          {flag.patient_name || flag.patient_id}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          {flag.patient_id}
                        </div>
                      </td>

                      <td style={{ padding: '12px 14px', maxWidth: '380px' }}>
                        <div style={{ fontWeight: '500', color: 'var(--text-primary)', marginBottom: '2px' }}>
                          {flag.explanation}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                          <strong>Record Reference:</strong> {flag.historical_reference}
                        </div>
                        {flag.resolution_note && (
                          <div style={{ fontSize: '11px', color: 'var(--success-green)', marginTop: '4px' }}>
                            <strong>Resolution:</strong> {flag.resolution_note}
                          </div>
                        )}
                      </td>

                      <td style={{ padding: '12px 14px' }}>
                        <span style={{
                          fontSize: '11px',
                          color: 'var(--text-secondary)',
                          background: 'var(--bg-surface-elevated)',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          border: '1px solid var(--border-subtle)'
                        }}>
                          {flag.root_cause === 'doctor_gap' && 'Doctor Oversight'}
                          {flag.root_cause === 'patient_gap' && 'Patient Omission'}
                          {flag.root_cause === 'no_fault' && 'Diagnostic Evolution / No Fault'}
                          {flag.root_cause === 'intentional' && 'Therapeutic Privilege'}
                        </span>
                      </td>

                      <td style={{ padding: '12px 14px' }}>
                        <span className={`badge ${isResolved ? 'badge-success' : isDismissed ? 'badge-neutral' : flag.status === 'UNDER_REVIEW' ? 'badge-medium' : 'badge-high'}`}>
                          {flag.status}
                        </span>
                      </td>

                      <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => handleOpenTimeline(flag.patient_id)}
                            className="btn btn-secondary btn-sm"
                            title="Inspect Patient Timeline"
                          >
                            <Eye size={13} />
                            Timeline
                          </button>

                          {!isResolved && !isDismissed && (
                            <>
                              {flag.status === 'OPEN' && (
                                <button
                                  onClick={() => handleStartReview(flag.id)}
                                  className="btn btn-secondary btn-sm"
                                >
                                  Review
                                </button>
                              )}
                              <button
                                onClick={() => {
                                  setShowResolveModal(flag);
                                  setResolutionNote('');
                                }}
                                className="btn btn-success btn-sm"
                              >
                                <Check size={13} />
                                Resolve
                              </button>
                              <button
                                onClick={() => {
                                  setShowDismissModal(flag);
                                  setDismissalReason('');
                                }}
                                className="btn btn-secondary btn-sm"
                              >
                                <X size={13} />
                                Dismiss
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pending Patient Corrections Section */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 18px',
        marginBottom: '28px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div>
            <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>
              Patient History Correction Suggestions
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Direct patient feedback on outdated medications, resolved allergies, or historical conditions.
            </div>
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {corrections.filter((c) => c.status === 'PENDING').length} Pending Review
          </div>
        </div>

        {corrections.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
            No pending patient correction suggestions.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '12px' }}>
            {corrections.map((corr) => (
              <div
                key={corr.id}
                style={{
                  background: 'var(--bg-surface-elevated)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '12px 14px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span className="badge badge-neutral">{corr.entity_type}</span>
                  <span className={`badge ${corr.status === 'ACCEPTED' ? 'badge-success' : corr.status === 'DISMISSED' ? 'badge-neutral' : 'badge-medium'}`}>
                    {corr.status}
                  </span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  Patient: <strong>{corr.patient_name || corr.patient_id}</strong>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                  Record Change: <span style={{ textDecoration: 'line-through', color: 'var(--text-muted)' }}>{corr.current_value}</span> &rarr; <strong>{corr.suggested_value}</strong>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: '10px' }}>
                  "{corr.note}"
                </div>

                {corr.status === 'PENDING' && (
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={() => handleAcceptCorrection(corr.id)} className="btn btn-success btn-sm">
                      <Check size={12} />
                      Accept & Update History
                    </button>
                    <button onClick={() => handleDismissCorrection(corr.id)} className="btn btn-secondary btn-sm">
                      <X size={12} />
                      Dismiss
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Diagnosis Intake Modal */}
      {showDiagnosisModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: '600' }}>Clinical Diagnosis & Prescription Entry</h2>
              <button onClick={() => setShowDiagnosisModal(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmitDiagnosis}>
              <div className="form-group">
                <label className="form-label">Patient</label>
                <select
                  value={diagForm.patient_id}
                  onChange={(e) => setDiagForm({ ...diagForm, patient_id: e.target.value })}
                  className="form-select"
                >
                  {patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name || p.id} ({p.id}) — Age {p.age}, {p.gender}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Diagnosis Name</label>
                <input
                  type="text"
                  required
                  value={diagForm.diagnosis_name}
                  onChange={(e) => setDiagForm({ ...diagForm, diagnosis_name: e.target.value })}
                  className="form-input"
                  placeholder="e.g. Acute Streptococcal Pharyngitis"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Clinical Note / Consultation Findings</label>
                <textarea
                  rows="3"
                  required
                  value={diagForm.clinical_note}
                  onChange={(e) => setDiagForm({ ...diagForm, clinical_note: e.target.value })}
                  className="form-textarea"
                  placeholder="Clinical documentation of examination..."
                ></textarea>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '10px' }}>
                <div className="form-group">
                  <label className="form-label">Prescription / Medication</label>
                  <input
                    type="text"
                    value={diagForm.medication}
                    onChange={(e) => setDiagForm({ ...diagForm, medication: e.target.value })}
                    className="form-input"
                    placeholder="e.g. Amoxicillin 500mg"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Dosage Regimen</label>
                  <input
                    type="text"
                    value={diagForm.dosage}
                    onChange={(e) => setDiagForm({ ...diagForm, dosage: e.target.value })}
                    className="form-input"
                    placeholder="e.g. TID x 7d"
                  />
                </div>
              </div>

              {/* Disclosure Control Module (PRD Section 20) */}
              <div style={{
                background: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-sm)',
                padding: '14px',
                marginTop: '10px',
                marginBottom: '16px',
              }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: '500' }}>
                  <input
                    type="checkbox"
                    checked={diagForm.disclose_to_patient}
                    onChange={(e) => setDiagForm({ ...diagForm, disclose_to_patient: e.target.checked })}
                  />
                  <span>Disclose directly to patient immediately</span>
                </label>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', marginLeft: '22px' }}>
                  Uncheck for therapeutic privilege, compassionate non-disclosure, or palliative staging.
                </p>

                {!diagForm.disclose_to_patient && (
                  <div style={{ marginTop: '12px' }}>
                    <div className="form-group">
                      <label className="form-label" style={{ color: 'var(--med-amber)' }}>
                        Therapeutic Privilege Justification (Required)
                      </label>
                      <input
                        type="text"
                        required
                        value={diagForm.disclosure_reason}
                        onChange={(e) => setDiagForm({ ...diagForm, disclosure_reason: e.target.value })}
                        className="form-input"
                        placeholder="e.g. Awaiting confirmatory biopsy; withhold to prevent severe acute distress"
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Staged Patient-Facing Summary (Shown in patient portal)</label>
                      <input
                        type="text"
                        value={diagForm.patient_facing_text}
                        onChange={(e) => setDiagForm({ ...diagForm, patient_facing_text: e.target.value })}
                        className="form-input"
                        placeholder="e.g. Follow-up imaging requested; routine checkup"
                      />
                    </div>
                    <p style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      Notice: The patient's authorized Guardian will receive immediate confidential notification with full clinical details.
                    </p>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" onClick={() => setShowDiagnosisModal(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={diagSubmitting} className="btn btn-primary">
                  {diagSubmitting ? 'Evaluating Reconciliation...' : 'Submit & Reconcile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resolve Modal */}
      {showResolveModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
              Resolve Clinical Flag: {showResolveModal.id}
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
              {showResolveModal.explanation}
            </p>
            <div className="form-group">
              <label className="form-label">Clinical Resolution Action & Note</label>
              <textarea
                rows="3"
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                className="form-textarea"
                placeholder="e.g. Discontinued Amoxicillin; prescribed Azithromycin 500mg daily due to confirmed Penicillin allergy."
              ></textarea>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={() => setShowResolveModal(null)} className="btn btn-secondary">Cancel</button>
              <button onClick={handleResolveFlag} className="btn btn-success">Confirm Resolution</button>
            </div>
          </div>
        </div>
      )}

      {/* Dismiss Modal */}
      {showDismissModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
              Dismiss Clinical Flag: {showDismissModal.id}
            </h2>
            <div className="form-group">
              <label className="form-label">Clinical Justification (Reason for Dismissal)</label>
              <textarea
                rows="3"
                value={dismissalReason}
                onChange={(e) => setDismissalReason(e.target.value)}
                className="form-textarea"
                placeholder="e.g. Clinical evolution confirmed by blood cultures; discrepancy noted but intentional."
              ></textarea>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={() => setShowDismissModal(null)} className="btn btn-secondary">Cancel</button>
              <button onClick={handleDismissFlag} className="btn btn-danger">Confirm Dismissal</button>
            </div>
          </div>
        </div>
      )}

      {/* Patient Medical Timeline Inspector Modal */}
      {timelinePatient && patientTimeline && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ padding: '24px', maxWidth: '750px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h2 style={{ fontSize: '16px', fontWeight: '600' }}>
                  Medical Timeline: {patientTimeline.patient.name || timelinePatient}
                </h2>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  ID: {patientTimeline.patient.id} | Age: {patientTimeline.patient.age} | {patientTimeline.patient.gender}
                </div>
              </div>
              <button onClick={() => setTimelinePatient(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>

            {/* Documented Allergies & Conditions */}
            <div style={{ display: 'flex', gap: '16px', background: 'var(--bg-surface-elevated)', padding: '10px 14px', borderRadius: '4px', marginBottom: '16px', fontSize: '12px' }}>
              <div>
                <strong style={{ color: 'var(--high-red)' }}>Allergies: </strong>
                {patientTimeline.patient.allergies?.length > 0 ? patientTimeline.patient.allergies.join(', ') : 'None documented'}
              </div>
              <div>
                <strong>Conditions: </strong>
                {patientTimeline.patient.conditions?.length > 0 ? patientTimeline.patient.conditions.join(', ') : 'None'}
              </div>
              <div>
                <strong>Medications: </strong>
                {patientTimeline.patient.medications?.length > 0 ? patientTimeline.patient.medications.join(', ') : 'None'}
              </div>
            </div>

            <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
              {patientTimeline.timeline.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>No recorded medical history.</p>
              ) : (
                <div style={{ borderLeft: '2px solid var(--border-default)', marginLeft: '12px', paddingLeft: '16px' }}>
                  {patientTimeline.timeline.map((item, idx) => (
                    <div key={idx} style={{ position: 'relative', marginBottom: '18px' }}>
                      <span style={{
                        position: 'absolute',
                        left: '-23px',
                        top: '4px',
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        background: item.type === 'ALLERGY' ? 'var(--high-red)' : item.type === 'FLAG' ? 'var(--med-amber)' : 'var(--accent-blue)',
                      }}></span>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {new Date(item.date).toLocaleDateString()}
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>
                        {item.title}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {item.description}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
