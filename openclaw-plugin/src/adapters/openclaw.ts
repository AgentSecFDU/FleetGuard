/**
 * OpenClawAdapter — OpenClaw Gateway integration for AgentFleetControl.
 *
 * Registers AgentFleetControl hooks with the OpenClaw plugin/extension system.
 * OpenClaw loads extensions from ~/.openclaw/extensions/.
 *
 * The extension manifest in package.json declares:
 *   "openclaw": { "pluginType": "governance", "hooks": [...] }
 */

import type {
  ToolCallContext, ToolResultContext, MessageContext, InstallContext,
} from '../types.js';
import type {
  AgentRuntimeAdapter, BeforeToolCallResult,
  MessageReceivedResult, BeforeInstallResult,
} from './interface.js';
import { AgentFleetControlPlugin } from '../core/plugin.js';

export class OpenClawAdapter implements AgentRuntimeAdapter {
  readonly name = 'openclaw';
  readonly version = '0.1.0';

  private plugin: AgentFleetControlPlugin;

  constructor(plugin: AgentFleetControlPlugin) {
    this.plugin = plugin;
  }

  async onBeforeToolCall(ctx: ToolCallContext): Promise<BeforeToolCallResult> {
    return this.plugin.onBeforeToolCall(ctx);
  }

  async onAfterToolCall(ctx: ToolResultContext): Promise<void> {
    return this.plugin.onAfterToolCall(ctx);
  }

  async onMessageReceived(ctx: MessageContext): Promise<MessageReceivedResult> {
    return this.plugin.onMessageReceived(ctx);
  }

  async onMessageSending(ctx: MessageContext): Promise<BeforeToolCallResult> {
    return this.plugin.onMessageSending(ctx);
  }

  async onBeforeInstall(ctx: InstallContext): Promise<BeforeInstallResult> {
    return this.plugin.onBeforeInstall(ctx);
  }

  async load(): Promise<void> {
    await this.plugin.initialize();
    // In production, OpenClaw would call this adapter's hooks via its
    // extension API. The adapter registers handlers matching the
    // extension manifest hooks declared in package.json.
    console.log(`[agentfleetcontrol] OpenClawAdapter loaded — governing tool calls`);
  }

  async unload(): Promise<void> {
    await this.plugin.shutdown();
  }
}
