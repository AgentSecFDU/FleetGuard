/**
 * FleetGuard Plugin — OpenClaw Governance Plugin
 * ===============================================
 *
 * Uses definePluginEntry-compatible default export with register(api).
 * Hooks are registered via api.on("hook_name", handler).
 *
 * Supported hooks: before_tool_call, after_tool_call, message_received,
 * message_sending, before_install.
 */

import { SidecarClient } from './client/sidecarClient.js';
import { beforeToolCall } from './hooks/beforeToolCall.js';
import { afterToolCall } from './hooks/afterToolCall.js';
import { messageReceived } from './hooks/messageReceived.js';
import { messageSending } from './hooks/messageSending.js';
import { beforeInstall } from './hooks/beforeInstall.js';
import { classifyTool } from './utils/classifyTool.js';
import type {
  ToolCallContext, ToolResultContext, MessageContext,
  InstallContext, SessionState,
} from './types.js';

// ── Plugin Configuration ──────────────────────────────────────────

const PLUGIN_NAME = 'fleetguard-openclaw-plugin';
const PLUGIN_VERSION = '0.1.0';
const SIDECAR_URL = process.env.FG_SIDECAR_URL || 'http://127.0.0.1:18900';

// ── Session Management ────────────────────────────────────────────

const sessions = new Map<string, SessionState>();

function getSession(sessionId: string): SessionState {
  let session = sessions.get(sessionId);
  if (!session) {
    session = {
      sessionId,
      hasUntrustedInput: false,
      pendingApprovals: new Set(),
      riskScore: 0,
    };
    sessions.set(sessionId, session);
  }
  return session;
}

const PLUGIN_DESCRIPTION =
  'FleetGuard AI governance plugin — intercepts tool calls, scans for prompt injection, ' +
  'detects secrets in messages, and enforces security policies via local Sidecar.';

// ── Default Export ────────────────────────────────────────────────

export default {
  id: 'fleetguard',
  name: 'FleetGuard',
  description: PLUGIN_DESCRIPTION,
  get configSchema() {
    return {
      type: 'object' as const,
      additionalProperties: false,
      properties: {
        enabled: {
          type: 'boolean' as const,
          description: 'Enable FleetGuard governance hooks.',
        },
      },
    };
  },

  register(api: any) {
    // Initialize Sidecar client
    const client = new SidecarClient(SIDECAR_URL);

    // Active flag: set to true after Sidecar connectivity is confirmed.
    // Hook handlers check this before processing.
    let pluginActive = false;

    // Fire-and-forget async init — must NOT block register().
    void (async () => {
      try {
        const status = await client.getStatus();
        pluginActive = true;
        console.log(
          `[${PLUGIN_NAME}] v${PLUGIN_VERSION} loaded — ` +
          `Sidecar: device=${status.device_id}, status=${status.status}`
        );
        // Report plugin_loaded
        await client.submitEvent({
          event_type: 'plugin_loaded',
          params_summary: `FleetGuard Plugin v${PLUGIN_VERSION} loaded`,
          risk_score: 0,
          risk_labels: [],
          content_uploaded: false,
        }).catch(() => {});
      } catch {
        console.warn(`[${PLUGIN_NAME}] ⚠️  Sidecar not reachable at ${SIDECAR_URL} — governance disabled`);
      }
    })();

    // ── Hook: before_tool_call ──────────────────────────────────
    api.on('before_tool_call', async (event: any, ctx: any) => {
      if (!pluginActive) return;

      const sessionId = ctx?.sessionId || ctx?.sessionKey || 'unknown';
      const session = getSession(sessionId);
      const toolName = event.toolName || 'unknown';
      const category = classifyTool(toolName);

      // Map OpenClaw event → ToolCallContext
      const toolCtx: ToolCallContext = {
        toolName,
        toolParams: event.params || {},
        sessionId,
        agentId: ctx?.agentId || 'unknown',
        runId: event.runId || ctx?.runId || '',
        inputProvenance: session.hasUntrustedInput ? 'untrusted_web' : 'trusted',
        sessionHasUntrustedInput: session.hasUntrustedInput,
      };

      const result = await beforeToolCall(toolCtx, client);

      if (result.action === 'block') {
        return { block: true, blockReason: result.reason };
      }
      if (result.action === 'require_approval') {
        return { requireApproval: { title: `${category}: ${toolName}`, description: result.reason } };
      }
    });

    // ── Hook: after_tool_call ───────────────────────────────────
    api.on('after_tool_call', async (event: any, ctx: any) => {
      if (!pluginActive) return;

      const toolCtx: ToolResultContext = {
        toolName: event.toolName || 'unknown',
        toolParams: event.params || {},
        result: typeof event.result === 'string' ? event.result : JSON.stringify(event.result || ''),
        isError: event.isError || false,
        sessionId: ctx?.sessionId || ctx?.sessionKey || 'unknown',
        agentId: ctx?.agentId || 'unknown',
        runId: event.runId || ctx?.runId || '',
      };

      await afterToolCall(toolCtx, client);
    });

    // ── Hook: message_received ─────────────────────────────────
    api.on('message_received', async (event: any, ctx: any) => {
      if (!pluginActive) return;

      const sessionId = ctx?.sessionKey || event.sessionKey || 'unknown';
      const session = getSession(sessionId);

      const msgCtx: MessageContext = {
        content: event.content || '',
        source: 'user',
        direction: 'incoming',
        sessionId,
        channel: ctx?.channelId,
      };

      const result = await messageReceived(msgCtx, client);

      if (result.hasInjectionPatterns || result.provenance.startsWith('untrusted')) {
        session.hasUntrustedInput = true;
      }
      session.riskScore = Math.min(session.riskScore + result.riskScore, 100);
    });

    // ── Hook: message_sending ──────────────────────────────────
    api.on('message_sending', async (event: any, ctx: any) => {
      if (!pluginActive) return;

      const sessionId = ctx?.sessionKey || event.sessionKey || 'unknown';
      const session = getSession(sessionId);

      const msgCtx: MessageContext = {
        content: event.content || event.text || '',
        source: 'agent',
        direction: 'outgoing',
        sessionId,
        recipient: event.to,
        channel: ctx?.channelId || event.channelId,
      };

      const result = await messageSending(msgCtx, client);

      if (result.action === 'block') {
        return { block: true, blockReason: result.reason };
      }
    });

    // ── Hook: before_install ───────────────────────────────────
    api.on('before_install', async (event: any, _ctx: any) => {
      if (!pluginActive) return;

      const installCtx: InstallContext = {
        type: event.installType === 'plugin' ? 'plugin' : 'skill',
        name: event.packageName || event.name || 'unknown',
        source: event.source || 'unknown',
        signature: event.hasSignature ? 'present' : undefined,
      };

      const result = await beforeInstall(installCtx, client);

      if (result.action === 'block') {
        return { block: true, blockReason: result.reason };
      }
      if (result.action === 'require_approval') {
        return { requireApproval: { title: 'Plugin Install', description: result.reason } };
      }
    });
  },
};
