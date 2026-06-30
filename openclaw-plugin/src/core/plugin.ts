/**
 * AgentFleetControlPlugin — runtime-agnostic governance core.
 *
 * This is the central engine shared across all agent runtime adapters.
 * It owns: session state, sidecar communication, tool classification,
 * parameter redaction, and the governance decision pipeline.
 *
 * Usage:
 *   const plugin = new AgentFleetControlPlugin({ sidecarUrl: "http://127.0.0.1:18900" });
 *   await plugin.initialize();
 *   // Then pass it to an adapter, e.g.:
 *   const adapter = new OpenClawAdapter(plugin);
 */

import { SidecarClient } from '../client/sidecarClient.js';
import { beforeToolCall } from '../hooks/beforeToolCall.js';
import { afterToolCall } from '../hooks/afterToolCall.js';
import { messageReceived } from '../hooks/messageReceived.js';
import { messageSending } from '../hooks/messageSending.js';
import { beforeInstall } from '../hooks/beforeInstall.js';
import type {
  ToolCallContext, ToolResultContext, MessageContext, InstallContext,
  SessionState,
} from '../types.js';
import type {
  BeforeToolCallResult, MessageReceivedResult, BeforeInstallResult,
} from '../adapters/interface.js';

export interface PluginConfig {
  sidecarUrl?: string;
}

const PLUGIN_NAME = 'agentfleetcontrol-plugin';
const PLUGIN_VERSION = '0.1.0';

export class AgentFleetControlPlugin {
  readonly name = PLUGIN_NAME;
  readonly version = PLUGIN_VERSION;

  private client: SidecarClient;
  private sessions = new Map<string, SessionState>();
  private _active = false;

  constructor(config: PluginConfig = {}) {
    this.client = new SidecarClient(config.sidecarUrl);
  }

  // ── Lifecycle ──────────────────────────────────────────────────

  async initialize(): Promise<void> {
    console.log(`[${PLUGIN_NAME}] v${this.version} initializing...`);
    try {
      const status = await this.client.getStatus();
      console.log(`[${PLUGIN_NAME}] Sidecar: device=${status.device_id} status=${status.status}`);
      this._active = true;
    } catch {
      console.warn(`[${PLUGIN_NAME}] Sidecar unreachable — governance bypassed`);
      this._active = false;
    }
    await this.client.submitEvent({
      event_type: 'plugin_loaded',
      params_summary: `AgentFleetControl Plugin v${PLUGIN_VERSION} loaded`,
      risk_score: 0, risk_labels: [], content_uploaded: false,
    }).catch(() => {});
  }

  async shutdown(): Promise<void> {
    this._active = false;
    await this.client.submitEvent({
      event_type: 'plugin_error',
      params_summary: 'Plugin unloaded',
      risk_score: 80, risk_labels: ['policy_drift_detected'], content_uploaded: false,
    }).catch(() => {});
  }

  get isActive(): boolean { return this._active; }

  // ── Session Management ─────────────────────────────────────────

  private getSession(sessionId: string): SessionState {
    let s = this.sessions.get(sessionId);
    if (!s) {
      s = { sessionId, hasUntrustedInput: false, pendingApprovals: new Set(), riskScore: 0 };
      this.sessions.set(sessionId, s);
    }
    return s;
  }

  // ── Hook Handlers (called by adapters) ─────────────────────────

  async onBeforeToolCall(ctx: ToolCallContext): Promise<BeforeToolCallResult> {
    if (!this._active) return { allow: true, reason: 'Plugin inactive' };
    const session = this.getSession(ctx.sessionId);
    ctx.sessionHasUntrustedInput = session.hasUntrustedInput;
    const result = await beforeToolCall(ctx, this.client);
    if (result.action === 'block') {
      session.riskScore += 50;
      return { allow: false, reason: result.reason };
    }
    if (result.action === 'require_approval' && result.approvalId) {
      session.pendingApprovals.add(result.approvalId);
    }
    return { allow: true, reason: result.reason };
  }

  async onAfterToolCall(ctx: ToolResultContext): Promise<void> {
    if (!this._active) return;
    await afterToolCall(ctx, this.client);
  }

  async onMessageReceived(ctx: MessageContext): Promise<MessageReceivedResult> {
    if (!this._active) return { provenance: 'unknown', hasInjection: false };
    const result = await messageReceived(ctx, this.client);
    const session = this.getSession(ctx.sessionId);
    if (result.hasInjectionPatterns || result.provenance.startsWith('untrusted')) {
      session.hasUntrustedInput = true;
    }
    session.riskScore = Math.min(session.riskScore + result.riskScore, 100);
    return { provenance: result.provenance, hasInjection: result.hasInjectionPatterns };
  }

  async onMessageSending(ctx: MessageContext): Promise<BeforeToolCallResult> {
    if (!this._active) return { allow: true, reason: 'Plugin inactive' };
    const result = await messageSending(ctx, this.client);
    return { allow: result.action === 'allow', reason: result.reason };
  }

  async onBeforeInstall(ctx: InstallContext): Promise<BeforeInstallResult> {
    if (!this._active) return { allow: true, reason: 'Plugin inactive' };
    const result = await beforeInstall(ctx, this.client);
    return { allow: result.action === 'allow', reason: result.reason };
  }

  getClient(): SidecarClient { return this.client; }
}
