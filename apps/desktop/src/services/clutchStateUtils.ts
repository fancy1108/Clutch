import type { ChatMessage, ClutchState } from '../types';

export function createSessionRunId(): string {
  return `run_${Date.now().toString(36)}`;
}

export function createEmptyState(runId: string): ClutchState {
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

export function isChatMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== 'object') return false;
  const msg = value as Record<string, unknown>;
  return typeof msg.id === 'string' && typeof msg.text === 'string';
}

export function createUserChatMessageHelper(text: string, avatar: string): ChatMessage {
  return {
    id: `user_${Date.now().toString(36)}`,
    agent: 'User',
    avatar,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    text: text.trim(),
  };
}

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
    toolSteps: incoming.toolSteps ?? existing.toolSteps,
    filesChanged: incoming.filesChanged ?? existing.filesChanged,
    planCard: incoming.planCard ?? existing.planCard,
    todoList: incoming.todoList ?? existing.todoList,
    questionCard: incoming.questionCard ?? existing.questionCard,
  };
}

export interface MergeChatMessagesOptions {
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

    // Same MCP approval intent must not duplicate Supervisor bubbles (message + patch race).
    const approvalKey =
      typeof (message as ChatMessage & { approvalKey?: string }).approvalKey === 'string'
        ? (message as ChatMessage & { approvalKey?: string }).approvalKey
        : undefined;
    if (message.agent === 'Supervisor' && approvalKey) {
      const priorApprovalIdx = merged.findIndex(
        (item) =>
          item.agent === 'Supervisor' &&
          (item as ChatMessage & { approvalKey?: string }).approvalKey === approvalKey,
      );
      if (priorApprovalIdx >= 0) {
        merged[priorApprovalIdx] = mergeMessageFields(merged[priorApprovalIdx], message);
        continue;
      }
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
  const preferredDispatch = preferred.dispatch_log ?? [];
  const patchDispatch = next.dispatch_log ?? [];
  if (preferredDispatch.length > patchDispatch.length) {
    next.dispatch_log = preferredDispatch;
  }
  const preferredLanes = preferred.pty_lanes ?? [];
  const patchLanes = next.pty_lanes ?? [];
  const preferredHasActiveLanes = preferredLanes.some((lane) => lane.status !== 'completed');
  const patchHasActiveLanes = patchLanes.some((lane) => lane.status !== 'completed');
  if (
    preferredDispatch.length > 0
    && !preferredHasActiveLanes
    && patchHasActiveLanes
  ) {
    next.pty_lanes = preferredLanes;
  } else if (preferredLanes.length > patchLanes.length) {
    next.pty_lanes = preferredLanes;
  }
  const preferredEdges = preferred.dispatch_edges ?? [];
  const patchEdges = next.dispatch_edges ?? [];
  if (preferredEdges.length > patchEdges.length) {
    next.dispatch_edges = preferredEdges;
  }
  return next;
}

export function shouldPreserveOptimisticRun(
  current: ClutchState,
  patch: Partial<ClutchState>,
): boolean {
  if (current.status !== 'running' || patch.status !== 'idle') return false;
  if (!current.workflow_id) return false;
  const incomingMessages = patch.messages;
  if (incomingMessages?.some((message) => message.agent !== 'User')) return false;
  return current.messages.some((message) => message.agent === 'User');
}
