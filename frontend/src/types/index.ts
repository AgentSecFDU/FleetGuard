// TypeScript type definitions matching FleetGuard API responses

// ── Auth ────────────────────────────────────────────────────────
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface DeviceEnrollRequest {
  enrollment_token: string;
  device_id: string;
  hostname: string;
  os: string;
  os_version?: string;
  username: string;
  openclaw_version?: string;
  plugin_version?: string;
  sidecar_version?: string;
}

export interface DeviceEnrollResponse {
  device_id: string;
  device_token: string;
  message: string;
}

export interface HeartbeatRequest {
  device_id: string;
  status?: string;
  current_sessions?: number;
  active_agent_runs?: number;
  policy_version?: number;
  quarantine?: boolean;
  timestamp: string;
}

export interface QuarantineRequest {
  reason: string;
}

export interface DevicePolicyResponse {
  device_id: string;
  policy_id: string;
  policy_version: number;
  yaml_content: string;
}

export interface AdminUser {
  username: string;
  role: string;
  is_active: boolean;
}

export interface Device {
  id: string;
  device_id: string;
  hostname: string;
  os: string;
  os_version: string | null;
  username: string;
  openclaw_version: string | null;
  plugin_version: string | null;
  sidecar_version: string | null;
  status: 'online' | 'offline' | 'quarantined';
  quarantine: boolean;
  quarantine_reason: string | null;
  quarantined_at: string | null;
  policy_id: string | null;
  policy_version: number;
  current_sessions: number;
  active_agent_runs: number;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Event {
  id: string;
  event_id: string;
  event_type: string;
  timestamp: string;
  device_id: string;
  hostname: string | null;
  user_id: string | null;
  session_id: string | null;
  agent_id: string | null;
  run_id: string | null;
  tool_name: string | null;
  tool_category: string | null;
  input_provenance: string | null;
  params_summary: string | null;
  params_redacted_json: Record<string, unknown> | null;
  risk_score: number;
  risk_labels_json: string[] | null;
  policy_decision: string | null;
  policy_id: string | null;
  policy_version: number | null;
  reason: string | null;
  severity: 'low' | 'medium' | 'high' | 'critical' | null;
  content_uploaded: boolean;
  created_at: string;
}

export interface Policy {
  id: string;
  policy_id: string;
  name: string;
  version: number;
  yaml_content: string;
  status: 'draft' | 'published' | 'archived';
  created_by: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PolicyVersion {
  version: number;
  status: string;
  published_at: string | null;
  created_at: string;
}

export interface Approval {
  id: string;
  approval_id: string;
  device_id: string;
  event_id: string | null;
  session_id: string | null;
  run_id: string | null;
  tool_name: string | null;
  params_summary: string | null;
  risk_score: number | null;
  risk_labels_json: string[] | null;
  reason: string | null;
  status: 'pending' | 'approved' | 'denied' | 'expired';
  requested_at: string;
  expires_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_reason: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  actor: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail_json: Record<string, unknown> | null;
  created_at: string;
}

export interface DashboardSummary {
  online_devices: number;
  quarantined_devices: number;
  total_events_24h: number;
  critical_events_24h: number;
  pending_approvals: number;
  avg_risk_score_24h: number;
}

export interface RiskTrendPoint {
  hour: string;
  low: number;
  medium: number;
  high: number;
  critical: number;
}

export interface TopRiskyDevice {
  device_id: string;
  hostname: string;
  username: string;
  avg_risk_score: number;
  critical_count: number;
}

export interface CriticalEvent {
  event_id: string;
  device_id: string;
  hostname: string | null;
  tool_name: string | null;
  tool_category: string | null;
  risk_score: number;
  reason: string | null;
  timestamp: string;
  event_type: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page?: number;
    page_size?: number;
    total?: number;
    cursor?: string | null;
    limit?: number;
  };
}
