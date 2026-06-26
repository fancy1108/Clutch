import { useSyncExternalStore } from 'react';
import type {
  ChatMessage,
  ClutchState,
  HybridExecutionData,
  HybridExecutionPayload,
  StatePatchData,
  WebSocketEnvelope,
} from '../types';
import { translateText, type Language } from '../components/LanguageContext';
import { sidecarWebSocketUrl } from './sidecarUrl';

export function createSessionRunId(): string {
  return `run_${Date.now().toString(36)}`;
}

function createEmptyState(runId: string): ClutchState {
  return {
    run_id: runId,
    workflow_id: '',
    current_instruction: '',
    active_node_id: '',
    active_agent: '',
    status: 'idle',
    messages: [],
    terminal_logs: [],
    changed_files: [],
    session_tokens: 0,
    session_cost_usd: 0,
    token_input: 0,
    token_output: 0,
  };
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== 'object') return false;
  const msg = value as Record<string, unknown>;
  return typeof msg.id === 'string' && typeof msg.text === 'string';
}

export const USER_CHAT_AVATAR =
  'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=100';

export function createUserChatMessage(text: string): ChatMessage {
  return {
    id: `user_${Date.now().toString(36)}`,
    agent: 'User',
    avatar: USER_CHAT_AVATAR,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    text: text.trim(),
  };
}

/** Keep optimistic chat rows when the server has not caught up yet. */
export function mergeMessageFields(existing: ChatMessage, incoming: ChatMessage): ChatMessage {
  const incomingEvents =
    incoming.outputEvents && incoming.outputEvents.length > 0
      ? incoming.outputEvents
      : undefined;
  return {
    ...existing,
    ...incoming,
    rawOutput: incoming.rawOutput || existing.rawOutput,
    outputEvents: incomingEvents ?? existing.outputEvents,
  };
}

export function mergeChatMessages(
  existing: ChatMessage[],
  incoming: ChatMessage[] | undefined,
): ChatMessage[] {
  if (!incoming) return existing;
  if (incoming.length === 0 && existing.length > 0) return existing;

  const merged = [...existing];
  const indexById = new Map(existing.map((message, index) => [message.id, index]));
  const userTexts = new Set(
    existing
      .filter((message) => message.agent === 'User')
      .map((message) => message.text.trim()),
  );

  for (const message of incoming) {
    const trimmed = message.text.trim();
    if (message.agent === 'User' && userTexts.has(trimmed)) {
      const existingIndex = merged.findIndex(
        (item) => item.agent === 'User' && item.text.trim() === trimmed,
      );
      if (existingIndex >= 0 && message.avatar && !merged[existingIndex].avatar) {
        merged[existingIndex] = { ...merged[existingIndex], avatar: message.avatar };
      }
      continue;
    }
    const priorIndex = indexById.get(message.id);
    if (priorIndex !== undefined) {
      merged[priorIndex] = mergeMessageFields(merged[priorIndex], message);
      continue;
    }
    merged.push(message);
    indexById.set(message.id, merged.length - 1);
    if (message.agent === 'User') {
      userTexts.add(trimmed);
    }
  }

  return merged;
}

export function shouldPreserveOptimisticRun(
  current: ClutchState,
  patch: Partial<ClutchState>,
): boolean {
  if (current.status !== 'running' || patch.status !== 'idle') return false;
  // Plain chat (no workflow) must accept idle after the assistant reply.
  if (!current.workflow_id) return false;
  const incomingMessages = patch.messages;
  if (incomingMessages?.some((message) => message.agent !== 'User')) return false;
  return current.messages.some((message) => message.agent === 'User');
}

class ClutchStateStore {
  private state: ClutchState = createEmptyState(createSessionRunId());
  private listeners = new Set<() => void>();
  private socket: WebSocket | null = null;
  private connectPromise: Promise<void> | null = null;
  private runId = this.state.run_id;
  private pendingHydrate: ClutchState | null = null;
  private pendingHybridExecutions = new Map<string, HybridExecutionPayload>();
  private _connected = false;

  get connected(): boolean {
    return this._connected;
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getSnapshot = (): ClutchState => this.state;

  replaceState = (state: ClutchState): void => {
    this.runId = state.run_id;
    this.state = state;
    this.emit();
  };

  /** Optimistic UI while POST /runs/{id}/start blocks on the first workflow node. */
  optimisticWorkflowStart = (params: {
    runId: string;
    workflowId: string;
    instruction: string;
    activeAgent?: string;
  }): void => {
    const trimmed = params.instruction.trim();
    if (!trimmed) return;

    const userMessage = createUserChatMessage(trimmed);
    if (this.state.run_id !== params.runId) {
      this.state = createEmptyState(params.runId);
    }

    const hasUserMessage = this.state.messages.some(
      (item) => item.agent === 'User' && item.text === trimmed,
    );

    this.applyPatch({
      run_id: params.runId,
      workflow_id: params.workflowId,
      status: 'running',
      current_instruction: trimmed,
      messages: hasUserMessage ? this.state.messages : [...this.state.messages, userMessage],
      active_agent: params.activeAgent || this.state.active_agent,
    });
  };

  setPendingHydrate = (state: ClutchState): void => {
    this.pendingHydrate = state;
  };

  private emit(): void {
    for (const listener of this.listeners) {
      listener();
    }
  }

  private applyPatch(patch: Partial<ClutchState>): void {
    const next: Partial<ClutchState> = { ...patch };
    if (next.messages !== undefined) {
      next.messages = mergeChatMessages(this.state.messages, next.messages);
    }
    if (next.hybrid_executions !== undefined) {
      next.hybrid_executions = {
        ...(this.state.hybrid_executions ?? {}),
        ...next.hybrid_executions,
      };
    }
    if (shouldPreserveOptimisticRun(this.state, next)) {
      delete next.status;
      if (!next.workflow_id && this.state.workflow_id) {
        delete next.workflow_id;
      }
      if (!next.current_instruction && this.state.current_instruction) {
        delete next.current_instruction;
      }
    }
    this.state = { ...this.state, ...next };
    this.emit();
  }

  private attachHybridExecution(data: HybridExecutionData): void {
    const messageId = data.messageId;
    if (!messageId) return;
    const payload: HybridExecutionPayload = {
      rawOutput: data.rawOutput,
      outputEvents: data.outputEvents,
    };
    const existingMessages = this.state.messages;
    const hasMessage = existingMessages.some((message) => message.id === messageId);
    if (!hasMessage) {
      this.pendingHybridExecutions.set(messageId, payload);
      return;
    }
    const messages = existingMessages.map((message) =>
      message.id === messageId
        ? mergeMessageFields(message, {
            ...message,
            rawOutput: payload.rawOutput ?? message.rawOutput,
            outputEvents: payload.outputEvents ?? message.outputEvents,
          })
        : message,
    );
    this.applyPatch({
      messages,
      hybrid_executions: {
        ...(this.state.hybrid_executions ?? {}),
        [messageId]: payload,
      },
    });
  }

  private applyPendingHybridExecution(message: ChatMessage): ChatMessage {
    const pending = this.pendingHybridExecutions.get(message.id);
    if (!pending) return message;
    this.pendingHybridExecutions.delete(message.id);
    this.applyPatch({
      hybrid_executions: {
        ...(this.state.hybrid_executions ?? {}),
        [message.id]: pending,
      },
    });
    return mergeMessageFields(message, {
      ...message,
      rawOutput: pending.rawOutput ?? message.rawOutput,
      outputEvents: pending.outputEvents ?? message.outputEvents,
    });
  }

  private appendMessage(message: ChatMessage): void {
    const enriched = this.applyPendingHybridExecution(message);
    if (this.state.messages.some((item) => item.id === enriched.id)) {
      this.applyPatch({
        messages: this.state.messages.map((item) =>
          item.id === enriched.id ? mergeMessageFields(item, enriched) : item,
        ),
      });
      return;
    }
    this.applyPatch({ messages: [...this.state.messages, enriched] });
  }

  private appendLog(line: string): void {
    if (!line || this.state.terminal_logs.at(-1) === line) return;
    this.applyPatch({ terminal_logs: [...this.state.terminal_logs, line] });
  }

  connect(runId: string = this.runId): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN && this.runId === runId) {
      return Promise.resolve();
    }

    if (this.connectPromise && this.runId === runId) {
      return this.connectPromise;
    }

    if (this.socket) {
      this.socket.close();
      this.socket = null;
      this._connected = false;
    }
    this.connectPromise = null;

    this.runId = runId;
    if (this.pendingHydrate?.run_id === runId) {
      this.state = this.pendingHydrate;
      this.pendingHydrate = null;
    } else if (this.state.run_id !== runId) {
      this.state = createEmptyState(runId);
    }
    this.emit();

    this.connectPromise = new Promise((resolve, reject) => {
      const ws = new WebSocket(sidecarWebSocketUrl(`/ws/runs/${runId}`));
      this.socket = ws;

      ws.onopen = () => {
        this._connected = true;
        console.log('%c[Clutch WS] Connected to sidecar', 'color: #22c55e; font-weight: bold;');
        resolve();
      };

      ws.onmessage = (event) => {
        try {
          const envelope = JSON.parse(event.data) as WebSocketEnvelope;
          if (envelope.event === 'state_patch') {
            const data = envelope.data as StatePatchData;
            this.applyPatch(data.patch);
            return;
          }
          if (envelope.event === 'message') {
            const data = envelope.data as { message?: unknown };
            if (isChatMessage(data.message)) {
              this.appendMessage(data.message);
            }
            return;
          }
          if (envelope.event === 'hybrid_execution') {
            this.attachHybridExecution(envelope.data as HybridExecutionData);
            return;
          }
          if (envelope.event === 'log') {
            const data = envelope.data as { message?: string };
            if (data.message) {
              this.appendLog(data.message);
            }
            return;
          }
          if (envelope.event === 'human_required') {
            this.applyPatch({ status: 'awaiting_human' });
            return;
          }
          if (envelope.event === 'validation_result') {
            const data = envelope.data as { passed?: boolean; message?: string };
            if (data.passed === false && data.message) {
              const lang = (localStorage.getItem('workspace_lang') as Language) || 'en';
              const nextStepsText = translateText(
                'Next steps: select "Bypass & Approve", "Reject & Redo" below, or type instructions and click "Retry".',
                lang
              );
              this.appendMessage({
                id: `validation-${Date.now()}`,
                agent: 'Evaluator',
                avatar: '',
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                text: `${data.message}\n\n${nextStepsText}`,
                status: 'FAILED',
                badgeText: 'VALIDATION FAILED',
              });
            }
            return;
          }
          if (envelope.event === 'file_changed') {
            window.dispatchEvent(new CustomEvent('clutch-file-changed', { detail: envelope.data }));
            return;
          }
          if (envelope.event === 'run_completed') {
            const data = envelope.data as { status?: string };
            if (data.status) {
              this.applyPatch({ status: data.status as ClutchState['status'] });
            }
          }
        } catch {
          console.warn('[Clutch WS] non-JSON message:', event.data);
        }
      };

      ws.onerror = () => {
        this.connectPromise = null;
        reject(new Error('WebSocket connection failed'));
      };

      ws.onclose = () => {
        this._connected = false;
        this.socket = null;
        this.connectPromise = null;
        this.emit();
      };
    });

    return this.connectPromise;
  }

  clearTerminalLogs(): void {
    this.applyPatch({ terminal_logs: [] });
  }

  async send(payload: Record<string, unknown>): Promise<void> {
    await this.connect(this.runId);
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }
    this.socket.send(JSON.stringify(payload));
  }
}

export const clutchStore = new ClutchStateStore();

export function useClutchState(): { state: ClutchState; connected: boolean } {
  const state = useSyncExternalStore(clutchStore.subscribe, clutchStore.getSnapshot);
  return { state, connected: clutchStore.connected };
}

export const connectSidecarWebSocket = (): Promise<void> =>
  clutchStore.connect(clutchStore.getSnapshot().run_id);

export const submitChatMessage = async (
  text: string,
  agentId?: string | null,
  modelId?: string | null,
): Promise<void> => {
  const payload: Record<string, unknown> = { text };
  if (agentId) payload.agent_id = agentId;
  if (modelId) payload.model_id = modelId;
  await clutchStore.send(payload);
};
