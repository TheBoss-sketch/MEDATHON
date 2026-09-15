/**
 * Centralized API client for MEDREA backend services.
 */

const API_BASE = '/api';

export function getAuthHeaders() {
  const token = localStorage.getItem('medrea_token');
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  };

  const response = await fetch(url, config);
  if (!response.ok) {
    let errorDetail = 'API Request Failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

// Auth API
export const loginUser = async (email, password) => {
  const data = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) {
    localStorage.setItem('medrea_token', data.access_token);
  }
  return data;
};

export const registerUser = (userData) =>
  request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(userData),
  });

export const getMe = () => request('/auth/me');

// Patients & Timelines API
export const listPatients = () => request('/patients');
export const getTimeline = (patientId) => request(`/patients/${patientId}/timeline`);
export const getPatientRecord = (patientId) => request(`/patients/${patientId}/timeline`);

export const requestAccess = (patientId, notes) =>
  request('/patients/access-requests', {
    method: 'POST',
    body: JSON.stringify({ patient_id: patientId, notes }),
  });

export const listAccessRequests = () => request('/patients/access-requests/list');

export const respondAccessRequest = (requestId, approve) =>
  request(`/patients/access-requests/${requestId}/respond`, {
    method: 'POST',
    body: JSON.stringify({ approve }),
  });

// Diagnoses Intake API
export const createDiagnosis = (diagData) =>
  request('/diagnoses', {
    method: 'POST',
    body: JSON.stringify(diagData),
  });

export const listDiagnosesForPatient = (patientId) =>
  request(`/diagnoses/patient/${patientId}`);

// Flags & Review Actions API
export const listFlags = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return request(`/flags${query ? '?' + query : ''}`);
};

export const getFlagStats = () => request('/flags/stats');

export const reviewFlag = (flagId) =>
  request(`/flags/${flagId}/review`, { method: 'POST' });

export const resolveFlag = (flagId, resolutionNote) =>
  request(`/flags/${flagId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ resolution_note: resolutionNote }),
  });

export const dismissFlag = (flagId, dismissalReason) =>
  request(`/flags/${flagId}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ dismissal_reason: dismissalReason }),
  });

// Patient Corrections API
export const submitCorrection = (corrData) =>
  request('/corrections', {
    method: 'POST',
    body: JSON.stringify(corrData),
  });

export const listCorrections = () => request('/corrections');

export const acceptCorrection = (corrId) =>
  request(`/corrections/${corrId}/accept`, { method: 'POST' });

export const dismissCorrection = (corrId, reason) =>
  request(`/corrections/${corrId}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ dismissal_reason: reason }),
  });

// Notifications API
export const listNotifications = () => request('/notifications');
export const getNotifications = () => request('/notifications');
export const markNotificationRead = (notifId) =>
  request(`/notifications/${notifId}/read`, { method: 'PATCH' });

export const markAllNotificationsRead = () =>
  request('/notifications/read-all', { method: 'POST' });

// Audit Logs API
export const listAuditLogs = () => request('/audit-logs?limit=50');

// Manual Trigger for Pager Demo
export const triggerTestAlert = (alertData) =>
  request('/alerts/test', {
    method: 'POST',
    body: JSON.stringify(alertData),
  });

export const api = {
  login: loginUser,
  register: registerUser,
  getMe,
  listPatients,
  getTimeline,
  getPatientRecord,
  requestAccess,
  listAccessRequests,
  respondAccessRequest,
  createDiagnosis,
  listDiagnosesForPatient,
  listFlags,
  getFlagStats,
  reviewFlag,
  resolveFlag,
  dismissFlag,
  submitCorrection,
  listCorrections,
  acceptCorrection,
  dismissCorrection,
  getNotifications,
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  listAuditLogs,
  triggerTestAlert,
};
