import { useSyncExternalStore } from 'react';
import type {
  ChatMessage,
  ClutchState,
  DispatchLogEntry,
  DispatchPreviewPayload,
  HybridExecutionData,
  HybridExecutionPayload,
  PtyOutputData,
  PtySessionStatusData,
  StatePatchData,
  WebSocketEnvelope,
} from '../types';
import { translateText, type Language } from '../components/LanguageContext';
import { mergeDispatchLogs } from './terminalOrchestraUtils';
import { sidecarWebSocketUrl } from './sidecarUrl';
import defaultAvatar from '../assets/default_avatar.jpg';
import {
  createSessionRunId,
  createEmptyState,
  isChatMessage,
  createUserChatMessageHelper,
  mergeMessageFields,
  isAuthoritativeMessageReplacement,
  mergeChatMessages,
  preferRicherSessionPatch,
  shouldPreserveOptimisticRun,
} from './clutchStateUtils';

export {
  createSessionRunId,
  mergeMessageFields,
  isAuthoritativeMessageReplacement,
  mergeChatMessages,
  preferRicherSessionPatch,
  shouldPreserveOptimisticRun,
};

export let USER_CHAT_AVATAR = defaultAvatar;

export function setUserChatAvatar(avatar: string) {
  USER_CHAT_AVATAR = avatar || defaultAvatar;
  clutchStore.triggerUpdate();
}

export function createUserChatMessage(text: string): ChatMessage {
  return createUserChatMessageHelper(text, USER_CHAT_AVATAR);
}

type LanePtyHandlers = {
  status: string;
  detail: string;
  outputHandlers: Set<(chunk: string) => void>;
  statusHandlers: Set<(status: string) => void>;
};

type DispatchPreviewResult =
  | { ok: true; preview: DispatchPreviewPayload }
  | { ok: false; error: string };

export type PtySessionStats = {
  total: number;
  sessions: Array<{ session_key: string; lane_id: string; cli_tool: string }>;
};

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
  private _ptySessionStatus = '';
  private _ptyOutputHandlers = new Set<(chunk: string) => void>();
  private _ptyStatusHandlers = new Set<(status: string) => void>();
  private _lanePty = new Map<string, LanePtyHandlers>();
  private _laneTranscripts = new Map<string, string>();
  private static readonly MAX_LANE_TRANSCRIPT_CHARS = 200_000;
  private _dispatchPreviewResolvers: Array<(result: DispatchPreviewResult) => void> = [];
  private _dispatchErrorHandlers = new Set<(error: string) => void>();
  private _ptyStatsResolvers: Array<(stats: PtySessionStats) => void> = [];
  private _ptyClosedHandlers = new Set<() => void>();
  private _lanePtyOps = new Map<string, Promise<void>>();
  private pendingOptimisticDispatchIds = new Set<string>();

  get connected(): boolean {
    return this._connected;
  }

  private lanePty(laneId: string): LanePtyHandlers {
    const key = laneId || 'primary';
    let lane = this._lanePty.get(key);
    if (!lane) {
      lane = { status: '', detail: '', outputHandlers: new Set(), statusHandlers: new Set() };
      this._lanePty.set(key, lane);
    }
    return lane;
  }

  /** `primary` and `lane_primary` refer to the same interactive PTY lane. */
  private lanePtyAliasKeys(laneId: string): string[] {
    const key = (laneId || 'primary').trim() || 'primary';
    if (key === 'primary' || key === 'lane_primary') {
      return ['lane_primary', 'primary'];
    }
    return [key];
  }

  private mirrorLanePtyStatus(status: string, laneId: string, detail = ''): void {
    for (const key of this.lanePtyAliasKeys(laneId)) {
      const lane = this.lanePty(key);
      lane.status = status;
      if (detail) {
        lane.detail = detail;
      } else if (status === 'booting' || status === 'ready') {
        lane.detail = '';
      }
      for (const handler of lane.statusHandlers) {
        handler(status);
      }
    }
  }

  private resolveFocusedLaneId(): string {
    const focusId = this.state.focused_lane_id;
    if (focusId) return focusId;
    const focused = this.state.pty_lanes?.find((lane) => lane.focused);
    return focused?.lane_id ?? 'primary';
  }

  private enqueueLanePtyOp(laneId: string, op: () => Promise<void>): Promise<void> {
    const key = laneId || 'primary';
    const prev = this._lanePtyOps.get(key) ?? Promise.resolve();
    const next = prev.then(op, op).finally(() => {
      if (this._lanePtyOps.get(key) === next) {
        this._lanePtyOps.delete(key);
      }
    });
    this._lanePtyOps.set(key, next);
    return next;
  }

  waitForLanePtyReady(laneId: string, timeoutMs = 15_000): Promise<boolean> {
    return this.waitForLanePtyReadyInternal(laneId, timeoutMs);
  }

  get ptySessionStatus(): string {
    return this._ptySessionStatus;
  }

  getLanePtyStatus(laneId: string): string {
    for (const key of this.lanePtyAliasKeys(laneId)) {
      const status = this.lanePty(key).status;
      if (status) return status;
    }
    return '';
  }

  getLanePtyDetail(laneId: string): string {
    for (const key of this.lanePtyAliasKeys(laneId)) {
      const detail = this.lanePty(key).detail;
      if (detail) return detail;
    }
    return '';
  }

  getLaneTranscript(laneId: string): string {
    return this.readLaneTranscript(laneId);
  }

  private normalizeLaneTranscriptKey(laneId: string): string {
    const raw = (laneId || 'primary').trim() || 'primary';
    if (raw === 'primary') return 'lane_primary';
    return raw;
  }

  private readLaneTranscript(laneId: string): string {
    const key = this.normalizeLaneTranscriptKey(laneId);
    return (
      this._laneTranscripts.get(key)
      ?? this._laneTranscripts.get(laneId)
      ?? (key !== 'primary' ? this._laneTranscripts.get('primary') : undefined)
      ?? ''
    );
  }

  private appendLaneTranscript(laneId: string, chunk: string): void {
    if (!chunk) return;
    const key = this.normalizeLaneTranscriptKey(laneId || this.resolveFocusedLaneId());
    const prev = this._laneTranscripts.get(key) ?? '';
    const next = (prev + chunk).slice(-ClutchStateStore.MAX_LANE_TRANSCRIPT_CHARS);
    this._laneTranscripts.set(key, next);
  }

  onPtyOutput(handler: (chunk: string) => void): () => void {
    this._ptyOutputHandlers.add(handler);
    return () => this._ptyOutputHandlers.delete(handler);
  }

  onPtyOutputForLane(laneId: string, handler: (chunk: string) => void): () => void {
    const lane = this.lanePty(laneId);
    lane.outputHandlers.add(handler);
    return () => lane.outputHandlers.delete(handler);
  }

  onPtyStatusChange(handler: (status: string) => void): () => void {
    this._ptyStatusHandlers.add(handler);
    return () => this._ptyStatusHandlers.delete(handler);
  }

  onPtyStatusChangeForLane(laneId: string, handler: (status: string) => void): () => void {
    const lane = this.lanePty(laneId);
    lane.statusHandlers.add(handler);
    return () => lane.statusHandlers.delete(handler);
  }

  onDispatchError(handler: (error: string) => void): () => void {
    this._dispatchErrorHandlers.add(handler);
    return () => this._dispatchErrorHandlers.delete(handler);
  }

  private dispatchPtyOutput(chunk: string, laneId = ''): void {
    this.appendLaneTranscript(laneId, chunk);
    const resolvedLaneId = laneId || this.resolveFocusedLaneId();
    const lane = resolvedLaneId ? this.lanePty(resolvedLaneId) : null;
    const aliasLane =
      resolvedLaneId === 'lane_primary'
        ? this.lanePty('primary')
        : resolvedLaneId === 'primary'
          ? this.lanePty('lane_primary')
          : null;
    for (const target of [lane, aliasLane]) {
      if (!target) continue;
      for (const handler of target.outputHandlers) {
        handler(chunk);
      }
    }
    for (const handler of this._ptyOutputHandlers) {
      handler(chunk);
    }
  }

  private setPtySessionStatus(status: string, laneId = '', detail = ''): void {
    if (laneId) {
      this.mirrorLanePtyStatus(status, laneId, detail);
    }
    this._ptySessionStatus = status;
    for (const handler of this._ptyStatusHandlers) {
      handler(status);
    }
  }

  async attachInteractivePty(
    cliTool: string,
    laneId?: string,
    options?: { configuredAgentId?: string },
  ): Promise<void> {
    const resolvedLane = laneId || this.resolveFocusedLaneId();
    return this.enqueueLanePtyOp(resolvedLane, async () => {
      this.setPtySessionStatus('booting', resolvedLane);
      const payload: Record<string, unknown> = {
        action: 'pty_attach',
        cli_tool: cliTool,
        lane_id: resolvedLane,
      };
      const configuredAgentId = options?.configuredAgentId?.trim();
      if (configuredAgentId) {
        payload.configured_agent_id = configuredAgentId;
      }
      await this.send(payload);
    });
  }

  async detachInteractivePty(laneId?: string): Promise<void> {
    const resolvedLane = laneId || this.resolveFocusedLaneId();
    return this.enqueueLanePtyOp(resolvedLane, async () => {
      await this.send({ action: 'pty_detach', lane_id: resolvedLane });
    });
  }

  async sendPtyInput(data: string, laneId?: string): Promise<void> {
    if (!data) return;
    const resolvedLane = laneId || this.resolveFocusedLaneId();
    await this.send({ action: 'pty_input', data, lane_id: resolvedLane });
  }

  async sendPtyResize(cols: number, rows: number, laneId?: string): Promise<void> {
    const resolvedLane = laneId || this.resolveFocusedLaneId();
    await this.send({ action: 'pty_resize', cols, rows, lane_id: resolvedLane });
  }

  private async delay(ms: number): Promise<void> {
    await new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  private async waitForLanePtyReadyInternal(laneId: string, timeoutMs = 15_000): Promise<boolean> {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      const status = this.getLanePtyStatus(laneId);
      if (status === 'ready') return true;
      if (status === 'blocked' || status === 'exited') return false;
      await this.delay(100);
    }
    return this.getLanePtyStatus(laneId) === 'ready';
  }

  /** Submit prompt to lane PTY after attach is ready (text + Enter). */
  async submitPtyPrompt(
    laneId: string,
    prompt: string,
    options?: { warmupMs?: number },
  ): Promise<boolean> {
    const text = prompt.trim();
    if (!text || !laneId) return false;

    const ready = await this.waitForLanePtyReadyInternal(laneId, 20_000);
    if (!ready) return false;

    const warmupMs = options?.warmupMs ?? 0;
    if (warmupMs > 0) {
      await this.delay(warmupMs);
    }

    try {
      await this.sendPtyInput(text, laneId);
      await this.delay(150);
      await this.sendPtyInput('\r', laneId);
      return true;
    } catch {
      return false;
    }
  }

  async ackPendingPtyInject(): Promise<void> {
    await this.connect(this.runId);
    await this.send({ action: 'pty_inject_ack' });
  }

  /** @deprecated Prefer pending_pty_inject + submitPtyPrompt after lane attach. */
  injectPtyPrompt(laneId: string, prompt: string): void {
    void this.submitPtyPrompt(laneId, prompt);
  }

  /** @deprecated Dispatch now sets pending_pty_inject; lane pane submits after PTY ready. */
  async injectDispatchPrompt(_targetDisplayName: string, _task: string): Promise<void> {
    return;
  }

  async previewDispatch(text: string): Promise<DispatchPreviewResult> {
    await this.connect(this.runId);
    return new Promise<DispatchPreviewResult>((resolve) => {
      this._dispatchPreviewResolvers.push(resolve);
      void this.send({ action: 'dispatch_preview', text }).catch(() => {
        const resolver = this._dispatchPreviewResolvers.pop();
        resolver?.({ ok: false, error: 'WebSocket send failed' });
      });
    });
  }

  async confirmDispatch(
    text: string,
    activeChips?: string[],
    targetAgent?: { id?: string; name?: string },
    laneTranscripts?: Array<{ lane_id: string; agent: string; transcript: string }>,
  ): Promise<void> {
    const payload: Record<string, unknown> = { action: 'dispatch_confirm', text };
    if (activeChips) payload.active_sources = activeChips;
    if (targetAgent?.id?.trim()) payload.target_configured_agent_id = targetAgent.id.trim();
    if (targetAgent?.name?.trim()) payload.target_configured_agent_name = targetAgent.name.trim();
    if (laneTranscripts && laneTranscripts.length > 0) payload.lane_transcripts = laneTranscripts;
    await this.send(payload);
  }

  /** Optimistic Overview dispatch row — shown before confirm_dispatch state_patch arrives. */
  optimisticDispatchLogAppend(entry: DispatchLogEntry): void {
    this.pendingOptimisticDispatchIds.add(entry.id);
    this.state = {
      ...this.state,
      dispatch_log: [...(this.state.dispatch_log ?? []), entry],
    };
    this.emit();
  }

  async focusLane(laneId: string): Promise<void> {
    await this.send({ action: 'lane_focus', lane_id: laneId });
  }

  async collapseLane(laneId: string, collapsed = true): Promise<void> {
    const normalizedId = laneId === 'primary' ? 'lane_primary' : laneId;
    const lanes = this.state.pty_lanes ?? [];
    if (lanes.length > 0) {
      this.applyPatch({
        pty_lanes: lanes.map((lane) => {
          const id = lane.lane_id === 'primary' ? 'lane_primary' : lane.lane_id;
          return id === normalizedId ? { ...lane, collapsed } : lane;
        }),
      });
    } else {
      this.applyPatch({
        pty_lanes: [{
          lane_id: normalizedId,
          agent_type: '',
          label: '',
          status: 'running',
          focused: !collapsed,
          collapsed,
          run_id: this.runId,
        }],
      });
    }
    await this.send({ action: 'lane_collapse', lane_id: normalizedId, collapsed });
  }

  async completeLane(laneId: string): Promise<void> {
    await this.send({ action: 'lane_complete', lane_id: laneId });
  }

  onPtySessionsClosed(handler: () => void): () => void {
    this._ptyClosedHandlers.add(handler);
    return () => this._ptyClosedHandlers.delete(handler);
  }

  async fetchPtySessionStats(): Promise<PtySessionStats> {
    await this.connect(this.runId);
    return new Promise<PtySessionStats>((resolve) => {
      this._ptyStatsResolvers.push(resolve);
      void this.send({ action: 'pty_session_stats' }).catch(() => {
        const resolver = this._ptyStatsResolvers.pop();
        resolver?.({ total: 0, sessions: [] });
      });
    });
  }

  async closeAllPtySessions(): Promise<void> {
    await this.connect(this.runId);
    await this.send({ action: 'pty_close_all' });
  }

  async closeOtherPtySessions(keepLaneIds: string[]): Promise<void> {
    await this.connect(this.runId);
    await this.send({ action: 'pty_close_others', keep_lane_ids: keepLaneIds });
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
    if (next.dispatch_log !== undefined) {
      next.dispatch_log = mergeDispatchLogs(this.state.dispatch_log ?? [], next.dispatch_log);
      for (const id of [...this.pendingOptimisticDispatchIds]) {
        const optimistic = (this.state.dispatch_log ?? []).find((entry) => entry.id === id);
        if (!optimistic) {
          this.pendingOptimisticDispatchIds.delete(id);
          continue;
        }
        const confirmed = next.dispatch_log.some(
          (entry) => entry.prompt === optimistic.prompt
            && entry.target === optimistic.target
            && !entry.id.startsWith('dispatch_opt_'),
        );
        if (confirmed) {
          this.pendingOptimisticDispatchIds.delete(id);
        }
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

  /** Public mirror for Design (and other non-WS) progress into the Terminal panel. */
  appendTerminalLog(line: string): void {
    this.appendLog(line);
  }

  connect(runId: string = this.runId): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN && this.runId === runId) {
      return Promise.resolve();
    }

    if (this.connectPromise && this.runId === runId) {
      return this.connectPromise;
    }

    if (this.socket) {
      this.socket.onmessage = null;
      this.socket.onclose = null;
      this.socket.onerror = null;
      this.socket.close();
      this.socket = null;
      this._connected = false;
    }
    this.connectPromise = null;
    if (this.runId !== runId) {
      this._laneTranscripts.clear();
    }
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

    this.connectPromise = sidecarWebSocketUrl(`/ws/runs/${runId}`).then(
      (wsUrl) =>
        new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(wsUrl);
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
            // Guard: discard stale patches from a previous connection
            if (data.patch?.run_id && data.patch.run_id !== this.runId) return;
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
                agent: 'AI Agent',
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
            return;
          }
          if (envelope.event === 'pty_output') {
            const data = envelope.data as PtyOutputData;
            if (data.chunk) {
              this.dispatchPtyOutput(data.chunk, data.lane_id ?? '');
            }
            return;
          }
          if (envelope.event === 'pty_session_status') {
            const data = envelope.data as PtySessionStatusData;
            if (data.status) {
              this.setPtySessionStatus(
                data.status,
                data.lane_id ?? '',
                typeof data.message === 'string' ? data.message : '',
              );
            }
            return;
          }
          if (envelope.event === 'dispatch_preview') {
            const data = envelope.data as {
              ok?: boolean;
              preview?: DispatchPreviewPayload;
              error?: string;
            };
            const resolver = this._dispatchPreviewResolvers.shift();
            if (resolver) {
              if (data.ok && data.preview) {
                resolver({ ok: true, preview: data.preview });
              } else {
                resolver({ ok: false, error: data.error ?? 'Dispatch preview failed' });
              }
            }
            return;
          }
          if (envelope.event === 'dispatch_error') {
            const data = envelope.data as { error?: string };
            const message = data.error ?? 'Dispatch failed';
            for (const handler of this._dispatchErrorHandlers) {
              handler(message);
            }
            return;
          }
          if (envelope.event === 'pty_session_stats') {
            const data = envelope.data as PtySessionStats & { run_id?: string };
            const resolver = this._ptyStatsResolvers.shift();
            resolver?.({
              total: data.total ?? 0,
              sessions: data.sessions ?? [],
            });
            return;
          }
          if (envelope.event === 'pty_sessions_closed') {
            for (const lane of this._lanePty.values()) {
              lane.status = 'detached';
            }
            this._ptySessionStatus = 'detached';
            for (const handler of this._ptyClosedHandlers) {
              handler();
            }
            return;
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
        }),
    );

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
