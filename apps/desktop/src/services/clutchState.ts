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
import defaultAvatar from '../assets/default_avatar.jpg';

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

export let USER_CHAT_AVATAR = defaultAvatar;

export function setUserChatAvatar(avatar: string) {
  USER_CHAT_AVATAR = avatar || defaultAvatar;
  clutchStore.triggerUpdate();
}

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

export interface MergeChatMessagesOptions {
  /** Client-generated id for the in-flight user turn (plain chat optimistic send). */
  pendingUserMessageId?: string | null;
}

export function isAuthoritativeMessageReplacement(
  existing: ChatMessage[],
  incoming: ChatMessage[],
): boolean {
  if (incoming.length >= existing.length) return false;
  const existingIds = new Set(existing.map((message) => message.id));
  return incoming.every((message) => existingIds.has(message.id));
}

export function mergeChatMessages(
  existing: ChatMessage[],
  incoming: ChatMessage[] | undefined,
  options?: MergeChatMessagesOptions,
): ChatMessage[] {
  if (!incoming) return existing;
  if (incoming.length === 0 && existing.length > 0) return existing;

  const merged = [...existing];
  const indexById = new Map(existing.map((message, index) => [message.id, index]));
  const pendingUserMessageId = options?.pendingUserMessageId ?? null;

  for (const message of incoming) {
    const trimmed = message.text.trim();
    const priorIndex = indexById.get(message.id);
    if (priorIndex !== undefined) {
      merged[priorIndex] = mergeMessageFields(merged[priorIndex], message);
      continue;
    }

    if (message.agent === 'User') {
      const priorSameIdx = merged.findIndex(
        (item) => item.agent === 'User' && item.text.trim() === trimmed,
      );
      if (priorSameIdx >= 0) {
        const isPendingTurn =
          Boolean(pendingUserMessageId) && message.id === pendingUserMessageId;
        if (!isPendingTurn) {
          if (message.avatar && !merged[priorSameIdx].avatar) {
            merged[priorSameIdx] = { ...merged[priorSameIdx], avatar: message.avatar };
          }
          continue;
        }
      }
    }

    merged.push(message);
    indexById.set(message.id, merged.length - 1);
  }

  return merged;
}

/** Prefer HTTP-hydrated session when WS reconnect snapshot is stale (HRT-09). */
export function preferRicherSessionPatch(
  preferred: ClutchState,
  patch: Partial<ClutchState>,
): Partial<ClutchState> {
  const next: Partial<ClutchState> = { ...patch };
  const preferredMessages = preferred.messages ?? [];
  const patchMessages = next.messages ?? [];
  if (preferredMessages.length > patchMessages.length) {
    next.messages = preferredMessages;
  }
  if (
    preferred.status === 'idle' &&
    preferredMessages.length > patchMessages.length
  ) {
    next.status = 'idle';
  }
  const preferredHybrid = preferred.hybrid_executions ?? {};
  const patchHybrid = next.hybrid_executions ?? {};
  if (Object.keys(preferredHybrid).length > Object.keys(patchHybrid).length) {
    next.hybrid_executions = { ...patchHybrid, ...preferredHybrid };
  }
  if (preferred.terminal_logs && preferred.terminal_logs.length > (next.terminal_logs?.length ?? 0)) {
    next.terminal_logs = preferred.terminal_logs;
  }
  return next;
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
  private reconnectHydrate: ClutchState | null = null;
  private backgroundHydrates = new Map<string, ReturnType<typeof setInterval>>();
  private backgroundSnapshots = new Map<string, ClutchState>();
  private pendingHybridExecutions = new Map<string, HybridExecutionPayload>();
  private pendingUserMessageId: string | null = null;
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

  /** After blocking workflow HTTP returns, keep richer incremental WS state when possible. */
  mergeWorkflowComplete = (remote: ClutchState): void => {
    const local = this.state;
    const localCount = local.messages?.length ?? 0;
    const remoteCount = remote.messages?.length ?? 0;
    if (local.run_id === remote.run_id && localCount >= remoteCount && localCount > 0) {
      this.applyPatch({
        status: remote.status,
        active_node_id: remote.active_node_id,
        active_agent: remote.active_agent,
        terminal_logs: remote.terminal_logs,
        hybrid_executions: remote.hybrid_executions,
        token_input: remote.token_input,
        token_output: remote.token_output,
        session_tokens: remote.session_tokens,
        session_cost_usd: remote.session_cost_usd,
      });
      return;
    }
    this.replaceState(remote);
  };

  /** Poll Sidecar HTTP state while a background plain-chat turn may still be running. */
  scheduleBackgroundHydrate = (
    runId: string,
    fetchState: (id: string) => Promise<ClutchState>,
  ): void => {
    if (this.backgroundHydrates.has(runId)) return;

    const poll = async () => {
      try {
        const remote = await fetchState(runId);
        this.backgroundSnapshots.set(runId, remote);

        if (this.runId !== runId) return;

        const localCount = this.state.messages?.length ?? 0;
        const remoteCount = remote.messages?.length ?? 0;
        if (
          remoteCount > localCount ||
          (remote.status === 'idle' && this.state.status === 'running' && remoteCount >= localCount)
        ) {
          this.state = {
            ...this.state,
            ...preferRicherSessionPatch(this.state, remote),
            messages: mergeChatMessages(this.state.messages, remote.messages),
          };
          this.emit();
        }
        if (remote.status !== 'running') {
          this.clearBackgroundHydrateForRun(runId);
        }
      } catch {
        // ignore transient fetch errors while polling
      }
    };

    void poll();
    this.backgroundHydrates.set(
      runId,
      setInterval(() => {
        void poll();
      }, 3000),
    );
  };

  clearBackgroundHydrateForRun = (runId: string): void => {
    const timer = this.backgroundHydrates.get(runId);
    if (timer) {
      clearInterval(timer);
      this.backgroundHydrates.delete(runId);
    }
  };

  clearBackgroundHydrate = (): void => {
    for (const runId of [...this.backgroundHydrates.keys()]) {
      this.clearBackgroundHydrateForRun(runId);
    }
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

    if (!hasUserMessage) {
      this.pendingUserMessageId = userMessage.id;
    }

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

  triggerUpdate(): void {
    this.emit();
  }

  private emit(): void {
    for (const listener of this.listeners) {
      listener();
    }
  }

  private applyPatch(patch: Partial<ClutchState>): void {
    const next: Partial<ClutchState> = { ...patch };
    if (next.messages !== undefined) {
      const incomingMessages = next.messages;
      if (isAuthoritativeMessageReplacement(this.state.messages, incomingMessages)) {
        next.messages = incomingMessages;
        if (next.hybrid_executions === undefined) {
          const incomingIds = new Set(incomingMessages.map((message) => message.id));
          const deletedIds = this.state.messages
            .filter((message) => !incomingIds.has(message.id))
            .map((message) => message.id);
          if (deletedIds.length > 0) {
            const hybrid = { ...(this.state.hybrid_executions ?? {}) };
            for (const id of deletedIds) {
              delete hybrid[id];
              this.pendingHybridExecutions.delete(id);
            }
            next.hybrid_executions = hybrid;
          }
        }
      } else {
        next.messages = mergeChatMessages(this.state.messages, incomingMessages, {
          pendingUserMessageId: this.pendingUserMessageId,
        });
      }
      if (
        this.pendingUserMessageId
        && next.messages.some((message) => message.id === this.pendingUserMessageId)
      ) {
        const pendingIndex = next.messages.findIndex(
          (message) => message.id === this.pendingUserMessageId,
        );
        const hasAgentAfterPending = pendingIndex >= 0
          && next.messages
            .slice(pendingIndex + 1)
            .some((message) => message.agent !== 'User' && message.agent !== 'System');
        if (hasAgentAfterPending) {
          this.pendingUserMessageId = null;
        }
      }
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
    if (enriched.agent === 'User') {
      const trimmed = enriched.text.trim();
      const isPendingTurn =
        Boolean(this.pendingUserMessageId) && enriched.id === this.pendingUserMessageId;
      if (!isPendingTurn) {
        const prior = this.state.messages.find(
          (item) => item.agent === 'User' && item.text.trim() === trimmed,
        );
        if (prior) {
          if (enriched.avatar && !prior.avatar) {
            this.applyPatch({
              messages: this.state.messages.map((item) =>
                item.id === prior.id ? { ...item, avatar: enriched.avatar } : item,
              ),
            });
          }
          return;
        }
      }
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
      this.reconnectHydrate = this.pendingHydrate;
      this.pendingHydrate = null;
    } else {
      const backgroundSnapshot = this.backgroundSnapshots.get(runId);
      if (backgroundSnapshot) {
        this.state = backgroundSnapshot;
        this.reconnectHydrate = backgroundSnapshot;
      } else if (this.state.run_id !== runId) {
        this.state = createEmptyState(runId);
        this.reconnectHydrate = null;
      }
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
            if (this.reconnectHydrate) {
              const preferred = this.reconnectHydrate;
              this.reconnectHydrate = null;
              this.applyPatch(preferRicherSessionPatch(preferred, data.patch));
              return;
            }
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

  clearShellSessionNotice(): void {
    if (!this.state.shell_session_status?.startsWith('rejected_')) return;
    this.applyPatch({ shell_session_status: 'ready' });
  }

  appendOptimisticUserMessage(text: string, messageId?: string): void {
    const trimmed = text.trim();
    if (!trimmed) return;
    const last = this.state.messages[this.state.messages.length - 1];
    if (last?.agent === 'User' && last.text.trim() === trimmed) return;
    const message = createUserChatMessage(trimmed);
    if (messageId) {
      message.id = messageId;
    }
    this.applyPatch({ messages: [...this.state.messages, message] });
  }

  /** Optimistic user row + running status while plain-chat WS turn starts. */
  optimisticPlainChatSend(text: string): string {
    const trimmed = text.trim();
    const last = this.state.messages[this.state.messages.length - 1];
    let messageId: string;
    const patch: Partial<ClutchState> = {};
    if (last?.agent === 'User' && last.text.trim() === trimmed) {
      messageId = last.id;
    } else {
      const message = createUserChatMessage(trimmed);
      messageId = message.id;
      patch.messages = [...this.state.messages, message];
    }
    this.pendingUserMessageId = messageId;
    if (this.state.status !== 'running') {
      patch.status = 'running';
    }
    if (Object.keys(patch).length > 0) {
      this.applyPatch(patch);
    }
    return messageId;
  }

  deleteMessage(messageId: string): void {
    const nextMessages = this.state.messages.filter((message) => message.id !== messageId);
    if (nextMessages.length === this.state.messages.length) return;

    if (this.pendingUserMessageId === messageId) {
      this.pendingUserMessageId = null;
    }

    const hybrid = { ...(this.state.hybrid_executions ?? {}) };
    delete hybrid[messageId];
    this.pendingHybridExecutions.delete(messageId);

    this.state = {
      ...this.state,
      messages: nextMessages,
      hybrid_executions: hybrid,
    };
    this.emit();
    void this.send({ action: 'delete_message', message_id: messageId });
  }

  clearWorkflowState(): void {
    this.applyPatch({ workflow_id: '' });
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
  clientMessageId?: string | null,
): Promise<void> => {
  const payload: Record<string, unknown> = { text };
  if (agentId) payload.agent_id = agentId;
  if (modelId) payload.model_id = modelId;
  if (clientMessageId) payload.client_message_id = clientMessageId;
  await clutchStore.send(payload);
};

export const clearWorkflowForSession = async (runId: string): Promise<void> => {
  await clutchStore.send({ action: 'clear_workflow' });
  clutchStore.clearWorkflowState();
};

export const deleteChatMessage = (messageId: string): void => {
  clutchStore.deleteMessage(messageId);
};
