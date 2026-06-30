/**
 * HermesAdapter — Hermes Agent runtime integration for AgentFleetControl.
 *
 * Placeholder: implement when Hermes Agent's hook/plugin API is defined.
 * Follows the same AgentRuntimeAdapter interface.
 */

import type {
  ToolCallContext, ToolResultContext, MessageContext, InstallContext,
} from '../types.js';
import type {
  AgentRuntimeAdapter, BeforeToolCallResult,
  MessageReceivedResult, BeforeInstallResult,
} from './interface.js';
import { AgentFleetControlPlugin } from '../core/plugin.js';

export class HermesAdapter implements AgentRuntimeAdapter {
  readonly name = 'hermes';
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
    console.log(`[agentfleetcontrol] HermesAdapter loaded`);
    // TODO: register hooks with Hermes runtime when its API is defined
  }

  async unload(): Promise<void> {
    await this.plugin.shutdown();
  }
}
