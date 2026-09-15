import React, { useState, useEffect } from "react";
import { listAuditLogs } from "../services/api";
import { ShieldCheck, X, Filter } from "lucide-react";

export default function AuditLogModal({ isOpen, onClose }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterAction, setFilterAction] = useState("ALL");

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const data = await listAuditLogs();
      setLogs(data);
    } catch (err) {
      console.error("Failed to load audit logs", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const filteredLogs = filterAction === "ALL" 
    ? logs 
    : logs.filter(l => l.action.toLowerCase().includes(filterAction.toLowerCase()));

  return (
    <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2000, padding: "1.5rem" }}>
      <div className="card" style={{ maxWidth: "900px", width: "100%", maxHeight: "90vh", display: "flex", flexDirection: "column", padding: 0, overflow: "hidden" }}>
        
        {/* Header */}
        <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--surface)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <ShieldCheck size={22} color="var(--primary)" />
            <div>
              <h3 style={{ margin: 0, fontSize: "1.15rem" }}>System Clinical Audit Trail (HIPAA / Compliance)</h3>
              <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Immutable record of all clinical access, intake events, and flag resolutions</span>
            </div>
          </div>
          <button className="btn btn-outline" style={{ padding: "0.4rem" }} onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Filter Toolbar */}
        <div style={{ padding: "0.75rem 1.5rem", background: "var(--surface-hover)", borderBottom: "1px solid var(--border-color)", display: "flex", alignItems: "center", gap: "1rem" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <Filter size={14} /> Filter Action:
          </span>
          <select 
            className="input-field" 
            style={{ width: "auto", padding: "0.3rem 0.6rem", fontSize: "0.85rem" }}
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
          >
            <option value="ALL">All Recorded Actions</option>
            <option value="DIAGNOSIS">Diagnosis Intake</option>
            <option value="FLAG">Flag Lifecycle</option>
            <option value="CORRECTION">Patient Corrections</option>
            <option value="ACCESS">Access Authorizations</option>
          </select>
          <span style={{ marginLeft: "auto", fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Showing {filteredLogs.length} events
          </span>
        </div>

        {/* Table Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
          {loading ? (
            <p style={{ textAlign: "center", color: "var(--text-muted)" }}>Loading audit entries...</p>
          ) : filteredLogs.length === 0 ? (
            <p style={{ textAlign: "center", color: "var(--text-muted)" }}>No audit records match the current filter.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-color)", color: "var(--text-muted)", textAlign: "left" }}>
                  <th style={{ padding: "0.5rem" }}>Timestamp</th>
                  <th style={{ padding: "0.5rem" }}>Actor</th>
                  <th style={{ padding: "0.5rem" }}>Action</th>
                  <th style={{ padding: "0.5rem" }}>Target Entity</th>
                  <th style={{ padding: "0.5rem" }}>Clinical Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: "1px solid var(--border-color)" }}>
                    <td style={{ padding: "0.6rem 0.5rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                      {new Date(log.timestamp || Date.now()).toLocaleString()}
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem" }}>
                      <strong>{log.actor_id || "System"}</strong>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{log.actor_role}</div>
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem" }}>
                      <span className="badge badge-low" style={{ fontSize: "0.75rem" }}>{log.action}</span>
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem", color: "var(--text-secondary)" }}>
                      <strong>{log.target_type}</strong>: {log.target_id}
                    </td>
                    <td style={{ padding: "0.6rem 0.5rem", color: "var(--text-secondary)", maxWidth: "300px", wordBreak: "break-word" }}>
                      {log.details || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: "0.75rem 1.5rem", borderTop: "1px solid var(--border-color)", background: "var(--surface)", display: "flex", justifyContent: "flex-end" }}>
          <button className="btn btn-outline" onClick={onClose}>Close</button>
        </div>

      </div>
    </div>
  );
}
