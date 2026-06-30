/**
 * AgentRuntimeAdapter — unified interface for all agent runtimes.
 *
 * To add a new agent runtime (OpenClaw, Hermes, etc.), implement this
 * interface and pass the adapter to AgentFleetControlPlugin.register().
 */

import type {
  ToolCallContext, ToolResultContext, MessageContext, InstallContext,
} from '../types.js';

export interface BeforeToolCallResult {
  allow: boolean;
  reason: string;
  approvalId?: string;
}

export interface MessageReceivedResult {
  provenance: 'trusted' | 'untrusted_web' | 'untrusted_file' | 'unknown';
  hasInjection: boolean;
}

export interface BeforeInstallResult {
  allow: boolean;
  reason: string;
}

export interface AgentRuntimeAdapter {
  /** Unique name for this runtime adapter (e.g. "openclaw", "hermes") */
  readonly name: string;
  readonly version: string;

  /**
   * Called by the runtime before executing a tool.
   * The adapter is responsible for calling AgentFleetControlPlugin.onBeforeToolCall().
   */
  onBeforeToolCall(ctx: ToolCallContext): Promise<BeforeToolCallResult>;

  /**
   * Called by the runtime after a tool completes.
   */
  onAfterToolCall(ctx: ToolResultContext): Promise<void>;

  /**
   * Called when the agent receives a message from any source.
   */
  onMessageReceived(ctx: MessageContext): Promise<MessageReceivedResult>;

  /**
   * Called before the agent sends a message externally.
   */
  onMessageSending(ctx: MessageContext): Promise<BeforeToolCallResult>;

  /**
   * Called before installing a skill or plugin.
   */
  onBeforeInstall(ctx: InstallContext): Promise<BeforeInstallResult>;

  /**
   * Lifecycle: called when the adapter is loaded.
   * Use this to register hooks with the runtime.
   */
  load(): Promise<void>;

  /**
   * Lifecycle: called when the adapter is unloaded.
   */
  unload(): Promise<void>;
}
