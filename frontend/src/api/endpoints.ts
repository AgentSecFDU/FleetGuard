import api from './client';
import type {
  LoginRequest, TokenResponse, DeviceEnrollRequest, DeviceEnrollResponse,
  HeartbeatRequest, QuarantineRequest, DevicePolicyResponse,
} from '../types';

// ── Auth ────────────────────────────────────────────────────────
export const authApi = {
  login: (data: { username: string; password: string }) =>
    api.post<TokenResponse>('/api/v1/auth/login', data),
  refresh: (refresh_token: string) =>
    api.post<TokenResponse>('/api/v1/auth/refresh', { refresh_token }),
  createEnrollmentToken: () =>
    api.post('/api/v1/auth/enrollment-token'),
  me: () => api.get('/api/v1/auth/me'),
};

// ── Devices ─────────────────────────────────────────────────────
export const devicesApi = {
  enroll: (data: DeviceEnrollRequest) =>
    api.post<DeviceEnrollResponse>('/api/v1/devices/enroll', data),
  heartbeat: (data: HeartbeatRequest) =>
    api.post('/api/v1/devices/heartbeat', data),
  list: (params?: Record<string, unknown>) =>
    api.get('/api/v1/devices/', { params }),
  get: (deviceId: string) =>
    api.get(`/api/v1/devices/${deviceId}`),
  quarantine: (deviceId: string, reason: string) =>
    api.post(`/api/v1/devices/${deviceId}/quarantine`, { reason }),
  unquarantine: (deviceId: string) =>
    api.post(`/api/v1/devices/${deviceId}/unquarantine`),
  getEvents: (deviceId: string, params?: Record<string, unknown>) =>
    api.get(`/api/v1/devices/${deviceId}/events`, { params }),
  getPolicy: (deviceId: string) =>
    api.get<DevicePolicyResponse>(`/api/v1/devices/${deviceId}/policy`),
};

// ── Events ──────────────────────────────────────────────────────
export const eventsApi = {
  uploadBatch: (events: unknown[]) =>
    api.post('/api/v1/events/batch', { events }),
  list: (params?: Record<string, unknown>) =>
    api.get('/api/v1/events/', { params }),
  get: (eventId: string) =>
    api.get(`/api/v1/events/${eventId}`),
};

// ── Policies ────────────────────────────────────────────────────
export const policiesApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/api/v1/policies/', { params }),
  create: (data: { policy_id: string; name: string; yaml_content: string }) =>
    api.post('/api/v1/policies/', data),
  get: (policyId: string) =>
    api.get(`/api/v1/policies/${policyId}`),
  update: (policyId: string, yaml_content: string) =>
    api.put(`/api/v1/policies/${policyId}`, { yaml_content }),
  publish: (policyId: string) =>
    api.post(`/api/v1/policies/${policyId}/publish`),
  getVersions: (policyId: string) =>
    api.get(`/api/v1/policies/${policyId}/versions`),
  validate: (data: { policy_id: string; name: string; yaml_content: string }) =>
    api.post('/api/v1/policies/validate', data),
};

// ── Approvals ───────────────────────────────────────────────────
export const approvalsApi = {
  create: (data: unknown) =>
    api.post('/api/v1/approvals/', data),
  list: (params?: Record<string, unknown>) =>
    api.get('/api/v1/approvals/', { params }),
  get: (approvalId: string) =>
    api.get(`/api/v1/approvals/${approvalId}`),
  approve: (approvalId: string, reason?: string) =>
    api.post(`/api/v1/approvals/${approvalId}/approve`, { reason }),
  deny: (approvalId: string, reason?: string, quarantine_device?: boolean) =>
    api.post(`/api/v1/approvals/${approvalId}/deny`, { reason, quarantine_device }),
};

// ── Audit ───────────────────────────────────────────────────────
export const auditApi = {
  list: (params?: Record<string, unknown>) =>
    api.get('/api/v1/audit/', { params }),
};

// ── Dashboard ───────────────────────────────────────────────────
export const dashboardApi = {
  summary: () => api.get('/api/v1/dashboard/summary'),
  riskTrends: (period = '24h') => api.get('/api/v1/dashboard/risk-trends', { params: { period } }),
  topRiskyDevices: (limit = 10) => api.get('/api/v1/dashboard/top-risky-devices', { params: { limit } }),
  recentCriticalEvents: (limit = 10) => api.get('/api/v1/dashboard/recent-critical-events', { params: { limit } }),
};
