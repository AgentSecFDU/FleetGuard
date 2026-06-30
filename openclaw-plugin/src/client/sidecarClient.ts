/**
 * HTTP client for communicating with the local AgentFleetControl Sidecar.
 *
 * The Sidecar runs on localhost:18900 by default and exposes:
 *   GET  /local/status
 *   GET  /local/policy
 *   POST /local/events       → { decision, reason, event_id }
 *   POST /local/approval/request → { approval_id, status }
 *   GET  /local/approval/:id/wait → { status, decision_reason }
 *   POST /local/quarantine/session
 *   POST /local/quarantine/device
 */

import type {
  EventPayload, PolicyDecision, ApprovalRequest,
  SidecarStatus,
} from '../types.js';

const DEFAULT_SIDECAR_URL = 'http://127.0.0.1:18900';

export class SidecarClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.AFC_SIDECAR_URL || DEFAULT_SIDECAR_URL;
  }

  /** Send an event to the Sidecar and get a policy decision back. */
  async submitEvent(event: EventPayload): Promise<PolicyDecision> {
    const resp = await fetch(`${this.baseUrl}/local/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    });
    if (!resp.ok) {
      // If Sidecar is unreachable, default-deny for high-risk, allow for low-risk
      if (event.risk_score >= 60) {
        return { decision: 'block', reason: 'Sidecar unreachable — default deny' };
      }
      return { decision: 'allow', reason: 'Sidecar unreachable — default allow' };
    }
    return resp.json();
  }

  /** Create an approval request for a high-risk action. */
  async requestApproval(req: ApprovalRequest): Promise<{ approval_id: string; status: string }> {
    const resp = await fetch(`${this.baseUrl}/local/approval/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!resp.ok) {
      throw new Error(`Approval request failed: ${resp.status}`);
    }
    return resp.json();
  }

  /** Long-poll for an approval decision (blocks until decided or timeout). */
  async waitApproval(approvalId: string): Promise<{ status: string; decision_reason?: string }> {
    const resp = await fetch(`${this.baseUrl}/local/approval/${approvalId}/wait`);
    if (!resp.ok) {
      return { status: 'expired', decision_reason: 'Sidecar unreachable — auto-denied' };
    }
    return resp.json();
  }

  /** Get the current cached policy from Sidecar. */
  async getPolicy(): Promise<unknown> {
    const resp = await fetch(`${this.baseUrl}/local/policy`);
    if (!resp.ok) throw new Error(`Failed to fetch policy: ${resp.status}`);
    return resp.json();
  }

  /** Get Sidecar status. */
  async getStatus(): Promise<SidecarStatus> {
    const resp = await fetch(`${this.baseUrl}/local/status`);
    if (!resp.ok) throw new Error(`Failed to fetch status: ${resp.status}`);
    return resp.json();
  }

  /** Quarantine a specific session. */
  async quarantineSession(sessionId: string, reason: string): Promise<void> {
    await fetch(`${this.baseUrl}/local/quarantine/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, reason }),
    });
  }

  /** Quarantine the entire device. */
  async quarantineDevice(reason: string): Promise<void> {
    await fetch(`${this.baseUrl}/local/quarantine/device`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
  }
}
