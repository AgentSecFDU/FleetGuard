/** Core type definitions for AgentFleetControl Plugin ↔ Sidecar communication. */

// ── OpenClaw Hook Contexts ────────────────────────────────────────

export interface ToolCallContext {
  toolName: string;
  toolParams: Record<string, unknown>;
  sessionId: string;
  agentId: string;
  runId: string;
  inputProvenance: 'trusted' | 'untrusted_web' | 'untrusted_file' | 'unknown';
  /** True if this session has previously seen untrusted input */
  sessionHasUntrustedInput: boolean;
}

export interface ToolResultContext {
  toolName: string;
  toolParams: Record<string, unknown>;
  result: string;
  isError: boolean;
  sessionId: string;
  agentId: string;
  runId: string;
}

export interface MessageContext {
  content: string;
  source: 'user' | 'agent' | 'tool_result' | 'external_api';
  direction: 'incoming' | 'outgoing';
  sessionId: string;
  recipient?: string;
  channel?: string;
}

export interface InstallContext {
  type: 'skill' | 'plugin';
  name: string;
  source: string;     // URL or registry name
  signature?: string; // Optional cryptographic signature
}

// ── Sidecar API types ─────────────────────────────────────────────

export interface EventPayload {
  event_type: string;
  tool_name?: string;
  tool_category?: string;
  input_provenance?: string;
  params_summary?: string;
  params_redacted?: Record<string, unknown>;
  session_id?: string;
  agent_id?: string;
  run_id?: string;
  risk_score: number;
  risk_labels: string[];
  content_uploaded: boolean;
}

export interface PolicyDecision {
  decision: 'allow' | 'log' | 'redact' | 'block' | 'require_approval';
  reason: string;
  event_id?: string;
}

export interface ApprovalRequest {
  approval_id: string;
  event_id: string;
  tool_name: string;
  params_summary: string;
  risk_score: number;
  risk_labels: string[];
  reason: string;
  session_id?: string;
  run_id?: string;
}

export interface SidecarStatus {
  device_id: string;
  hostname: string;
  status: 'online' | 'quarantined' | 'offline';
  quarantine: boolean;
  policy_version: number;
  control_center_url: string;
  control_center_reachable: boolean;
  queue_size: number;
}

// ── Plugin state ──────────────────────────────────────────────────

export interface SessionState {
  sessionId: string;
  hasUntrustedInput: boolean;
  pendingApprovals: Set<string>;
  riskScore: number;
}
