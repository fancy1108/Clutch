import type { PtyLane } from '@clutch/shared-types';

export const CLI_DISPLAY: Record<string, string> = {
  'claude-cli': 'Claude Code',
  'opencode-cli': 'OpenCode',
  'antigravity-cli': 'Antigravity CLI',
  'codex-cli': 'Codex CLI',
  'aider-cli': 'Aider CLI',
  'codebuddy-cli': 'CodeBuddy CLI',
  'rivet-cli': 'Rivet CLI',
  'ollama-cli': 'Ollama',
};

/** Dispatch @-mention targets shown in Orchestrator Bar picker (matches backend KNOWN_AGENTS). */
export const DISPATCH_MENTION_OPTIONS = Object.entries(CLI_DISPLAY).map(([agentType, mention]) => ({
  mention,
  agentType,
}));

export function agentDisplayName(agentType: string, agentName?: string): string {
  const custom = agentName?.trim();
  if (custom) return custom;
  return CLI_DISPLAY[agentType] ?? agentType;
}

/** Shared lane chrome — expanded pane shell and collapsed float card. */
export const LANE_SHELL_CLASS = 'rounded-2xl border border-neutral-800 bg-[#111111]';

export function laneShellBorderClass(focused: boolean): string {
  return focused ? 'border-neutral-700 ring-1 ring-neutral-600/80' : 'border-neutral-800';
}

export function resolveConfiguredAgentName(
  agentType: string,
  agents: Array<{ id?: string; name: string; agentType?: string }>,
  configuredAgentId?: string,
): string | undefined {
  const cfgId = configuredAgentId?.trim();
  if (cfgId) {
    const byId = agents.find((agent) => agent.id === cfgId);
    if (byId?.name?.trim()) return byId.name.trim();
  }
  const match = agents.find((agent) => agent.agentType === agentType);
  return match?.name?.trim() || undefined;
}

export function laneHeaderAgentName(
  lane: PtyLane,
  agents: Array<{ id?: string; name: string; agentType?: string }>,
): string {
  const configuredName = lane.configured_agent_name?.trim();
  if (configuredName) return configuredName;
  const configuredId = lane.configured_agent_id?.trim();
  if (configuredId) {
    const byId = agents.find((agent) => agent.id === configuredId);
    if (byId?.name?.trim()) return byId.name.trim();
  }
  return agentDisplayName(
    lane.agent_type,
    resolveConfiguredAgentName(lane.agent_type, agents, configuredId),
  );
}

export function formatInputMention(label: string): string {
  return `@${label} `;
}

const LAST_CLI_AGENT_STORAGE_KEY = 'clutch.last_cli_agent_id';

export function loadLastCliAgentId(): string | null {
  if (typeof localStorage === 'undefined') return null;
  const value = localStorage.getItem(LAST_CLI_AGENT_STORAGE_KEY)?.trim();
  return value || null;
}

export function saveLastCliAgentId(agentId: string): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(LAST_CLI_AGENT_STORAGE_KEY, agentId);
}

export type MentionableAgent = {
  id: string;
  name: string;
  dispatchTarget?: string;
};

function mentionBoundary(rest: string, labelLength: number): boolean {
  const next = rest[labelLength];
  return next === undefined || next === ' ' || next === '\n';
}

/** Resolve configured agent when preview target is a canonical dispatch label (e.g. OpenCode). */
export function resolveAgentFromDispatchTarget(
  target: string,
  agents: MentionableAgent[],
): { agentId: string; name: string } | null {
  const needle = (target ?? '').trim().toLowerCase();
  if (!needle || agents.length === 0) return null;

  const byName = agents.filter((agent) => agent.name.trim().toLowerCase() === needle);
  if (byName.length === 1) {
    return { agentId: byName[0].id, name: byName[0].name.trim() };
  }

  const byTarget = agents.filter(
    (agent) => agent.dispatchTarget?.trim().toLowerCase() === needle,
  );
  if (byTarget.length === 1) {
    return { agentId: byTarget[0].id, name: byTarget[0].name.trim() };
  }

  return null;
}

/** Resolve dispatch target agent from @-mention, footer selection, or canonical target. */
export function resolveDispatchTargetAgent(
  text: string,
  previewTarget: string,
  agents: MentionableAgent[],
  selectedAgentId?: string | null,
): { agentId: string; name: string } | null {
  const trimmedText = text.trim();
  const previewLabel = (previewTarget ?? '').trim();
  const isGraphHandoff = /\bfrom\s+@/i.test(trimmedText);

  // Graph handoff: @Target from @Source — target is always previewTarget, not the last @ in text.
  if (isGraphHandoff && previewLabel) {
    const fromPreview = resolveAgentFromDispatchTarget(previewTarget, agents);
    if (fromPreview) return fromPreview;
    return { agentId: selectedAgentId?.trim() || '', name: previewLabel };
  }

  const selectedId = selectedAgentId?.trim();
  const previewNeedle = previewLabel.toLowerCase();
  if (selectedId && previewNeedle) {
    const selected = agents.find((agent) => agent.id === selectedId);
    const ambiguousTarget = agents.filter(
      (agent) => agent.dispatchTarget?.trim().toLowerCase() === previewNeedle,
    );
    if (
      selected?.name?.trim()
      && ambiguousTarget.length > 1
      && trimmedText.toLowerCase().includes(`@${previewNeedle}`)
    ) {
      return { agentId: selected.id, name: selected.name.trim() };
    }
  }

  const fromPreview = resolveAgentFromDispatchTarget(previewTarget, agents);
  if (fromPreview) return fromPreview;

  const fromInput = parseInputAgentMention(text, agents);
  if (fromInput) return fromInput;

  if (selectedId) {
    const selected = agents.find((agent) => agent.id === selectedId);
    if (selected?.name?.trim()) {
      return { agentId: selected.id, name: selected.name.trim() };
    }
  }

  return null;
}

/** Match a completed @agent mention in input text (longest label wins). */
export function parseInputAgentMention(
  text: string,
  agents: MentionableAgent[],
): { agentId: string; name: string } | null {
  if (!text.includes('@') || agents.length === 0) return null;

  const sortedByName = [...agents].sort((a, b) => b.name.length - a.name.length);
  const sortedTargets = [...new Set(
    agents
      .map((agent) => agent.dispatchTarget?.trim())
      .filter((target): target is string => Boolean(target)),
  )].sort((a, b) => b.length - a.length);
  let best: { agentId: string; name: string; index: number } | null = null;

  for (let i = 0; i < text.length; i += 1) {
    if (text[i] !== '@') continue;
    if (i > 0 && text[i - 1] !== ' ' && text[i - 1] !== '\n') continue;

    const rest = text.slice(i + 1);
    let matched: { agentId: string; name: string } | null = null;

    for (const agent of sortedByName) {
      const name = agent.name.trim();
      if (!name || !rest.toLowerCase().startsWith(name.toLowerCase())) continue;
      if (!mentionBoundary(rest, name.length)) continue;
      matched = { agentId: agent.id, name };
      break;
    }

    if (!matched) {
      for (const target of sortedTargets) {
        if (!rest.toLowerCase().startsWith(target.toLowerCase())) continue;
        if (!mentionBoundary(rest, target.length)) continue;
        const candidates = agents.filter(
          (agent) => agent.dispatchTarget?.trim().toLowerCase() === target.toLowerCase(),
        );
        if (candidates.length !== 1) continue;
        matched = { agentId: candidates[0].id, name: candidates[0].name.trim() };
        break;
      }
    }

    if (matched && (!best || i >= best.index)) {
      best = { ...matched, index: i };
    }
  }

  return best ? { agentId: best.agentId, name: best.name } : null;
}

export type LaneGridLayout = 'single' | 'pair' | 'split-3' | 'quad';

/** Max two lanes per row; odd counts use two small + one large row. */
export function computeLaneLayout(expandedCount: number): LaneGridLayout {
  if (expandedCount <= 1) return 'single';
  if (expandedCount === 2) return 'pair';
  if (expandedCount === 3) return 'split-3';
  return 'quad';
}

/** Place focused lane in the prominent slot for split-3 (large bottom row). */
export function orderLanesForGrid(lanes: PtyLane[], layout: LaneGridLayout): PtyLane[] {
  if (layout !== 'split-3' || lanes.length !== 3) return lanes;
  const focusedIdx = lanes.findIndex((lane) => lane.focused);
  if (focusedIdx < 0) return lanes;
  const focused = lanes[focusedIdx];
  const rest = lanes.filter((_, i) => i !== focusedIdx);
  return [...rest, focused];
}

export function expandedLanes(lanes: PtyLane[]): PtyLane[] {
  return lanes.filter((lane) => !lane.collapsed && lane.status !== 'queued');
}

export function collapsedLanes(lanes: PtyLane[]): PtyLane[] {
  return lanes.filter((lane) => lane.collapsed || lane.status === 'queued');
}

export function findLaneForDispatchSource(lanes: PtyLane[], sourceLabel: string): PtyLane | null {
  const needle = sourceLabel.trim();
  if (!needle || needle === '工作区') return null;

  const byConfiguredName = lanes.filter(
    (lane) =>
      lane.configured_agent_name?.trim().toLowerCase() === needle.toLowerCase()
      && lane.status !== 'queued',
  );
  if (byConfiguredName.length === 1) return byConfiguredName[0];
  if (byConfiguredName.length > 1) {
    return byConfiguredName.find((lane) => !lane.collapsed) ?? byConfiguredName[0];
  }

  const agentType = resolveAgentTypeFromDispatchTarget(needle);
  if (!agentType) return null;
  const candidates = lanes.filter((lane) => lane.agent_type === agentType && lane.status !== 'queued');
  if (candidates.length === 0) return null;
  if (candidates.length === 1) return candidates[0];
  const byName = candidates.find(
    (lane) => lane.configured_agent_name?.trim().toLowerCase() === needle.toLowerCase(),
  );
  if (byName) return byName;
  return candidates.find((lane) => !lane.collapsed) ?? candidates[0];
}

export function collectHandoffLaneTranscripts(
  sources: string[],
  lanes: PtyLane[],
  getTranscript: (laneId: string) => string,
  targetAgent?: string,
): Array<{ lane_id: string; agent: string; transcript: string }> {
  const out: Array<{ lane_id: string; agent: string; transcript: string }> = [];
  const seen = new Set<string>();
  const targetType = targetAgent ? resolveAgentTypeFromDispatchTarget(targetAgent) : null;

  const pushLane = (lane: PtyLane, agentLabel: string) => {
    if (!lane || seen.has(lane.lane_id)) return;
    if (targetType && lane.agent_type === targetType) return;
    seen.add(lane.lane_id);
    const transcript = getTranscript(lane.lane_id).trim();
    if (transcript) {
      out.push({ lane_id: lane.lane_id, agent: agentLabel, transcript });
    }
  };

  for (const src of sources) {
    const lane = findLaneForDispatchSource(lanes, src);
    if (lane) pushLane(lane, src);
  }

  if (out.length === 0) {
    for (const lane of lanes) {
      if (lane.status === 'queued') continue;
      const label = lane.configured_agent_name?.trim() || agentDisplayName(lane.agent_type);
      pushLane(lane, label);
    }
  }

  return out;
}

/** Synthetic lane shown before the first dispatch when input already @-mentions an agent. */
export function buildPreviewPtyLane(agentType: string, sessionRunId: string): PtyLane {
  return {
    lane_id: 'lane_primary',
    agent_type: agentType,
    label: '',
    status: 'running',
    focused: true,
    collapsed: false,
    run_id: sessionRunId,
  };
}

/** Session has real dispatch records — terminals stay visible even when input is empty. */
export function sessionHasTerminalHistory(state: {
  dispatch_log?: unknown[];
}): boolean {
  return (state.dispatch_log ?? []).length > 0;
}

/** Session has chat messages or terminal dispatch records worth listing in history. */
export function sessionHasPersistableContent(state: {
  messages?: unknown[];
  dispatch_log?: unknown[];
}): boolean {
  return (state.messages?.length ?? 0) > 0 || (state.dispatch_log?.length ?? 0) > 0;
}

/** Session still has live (non-completed) terminal lanes. */
export function sessionHasActiveTerminalLanes(state: {
  pty_lanes?: Array<{ status?: string }>;
}): boolean {
  return (state.pty_lanes ?? []).some((lane) => lane.status !== 'completed');
}

/** Archived terminal session: left terminal, no live lanes — show read-only history in chat mode. */
export function isArchivedTerminalHistoryView(
  state: { dispatch_log?: unknown[]; pty_lanes?: Array<{ status?: string }> },
  workspaceViewMode: 'chat' | 'terminal',
): boolean {
  return workspaceViewMode === 'chat'
    && sessionHasTerminalHistory(state)
    && !sessionHasActiveTerminalLanes(state);
}

/**
 * Resume sidebar selection: persisted lanes may still be "running" after PTY close
 * or app restart even though no interactive terminal is attached.
 */
export function normalizeTerminalSessionForResume<T extends {
  dispatch_log?: unknown[];
  pty_lanes?: Array<{ status?: string }>;
}>(state: T): T {
  if (!sessionHasTerminalHistory(state)) return state;
  const lanes = state.pty_lanes ?? [];
  if (lanes.length === 0 || !sessionHasActiveTerminalLanes(state)) return state;
  return { ...state, pty_lanes: [] };
}

/** Whether leaving terminal mode should prompt the user first. */
export function shouldConfirmLeavingTerminal(
  state: { dispatch_log?: unknown[]; pty_lanes?: Array<{ status?: string }> },
  workspaceViewMode: 'chat' | 'terminal',
  orchestratorInput = '',
  agents: MentionableAgent[] = [],
): boolean {
  return shouldConfirmLeavingTerminalForNewChat(
    state,
    workspaceViewMode,
    orchestratorInput,
    agents,
  );
}

/** True when orchestrator input is empty or only an @Agent prefix with no task text. */
export function orchestratorInputHasUserTask(
  text: string,
  agents: MentionableAgent[],
): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;
  const mention = parseInputAgentMention(trimmed, agents);
  if (!mention) return true;
  const agent = agents.find((item) => item.id === mention.agentId);
  const labels = [mention.name, agent?.dispatchTarget?.trim()].filter(
    (label): label is string => Boolean(label?.trim()),
  );
  for (const label of labels) {
    const token = `@${label}`;
    const mentionStart = trimmed.toLowerCase().indexOf(token.toLowerCase());
    if (mentionStart < 0) continue;
    const afterMention = trimmed.slice(mentionStart + token.length).trim();
    return afterMention.length > 0;
  }
  return true;
}

/**
 * New Chat: skip confirm for fresh terminal sessions (preview PTY / default @ only).
 * Preview attach creates running lanes before dispatch — those are not protected work.
 */
export function shouldConfirmLeavingTerminalForNewChat(
  state: { dispatch_log?: unknown[]; pty_lanes?: Array<{ status?: string }> },
  workspaceViewMode: 'chat' | 'terminal',
  orchestratorInput = '',
  agents: MentionableAgent[] = [],
): boolean {
  if (workspaceViewMode !== 'terminal') return false;
  if (sessionHasTerminalHistory(state)) return true;
  return orchestratorInputHasUserTask(orchestratorInput, agents);
}

export function isHandoffDispatchEntry(entry: {
  dispatch_mode?: string;
  handoff_file?: string;
  handoff_path?: string;
}): boolean {
  if (entry.dispatch_mode === 'switch') return false;
  if (entry.dispatch_mode === 'handoff') return true;
  return Boolean(entry.handoff_file?.trim() && entry.handoff_path?.trim());
}

/** One visible lane per lane_id (session may have multiple agents / lanes). */
export function uniqueLanesByLaneId(lanes: PtyLane[]): PtyLane[] {
  const seen = new Set<string>();
  return lanes.filter((lane) => {
    if (seen.has(lane.lane_id)) return false;
    seen.add(lane.lane_id);
    return true;
  });
}

/** @deprecated Prefer uniqueLanesByLaneId for multi-lane handoff sessions. */
export function dedupeLanesByAgentType(lanes: PtyLane[]): PtyLane[] {
  const score = (lane: PtyLane): number =>
    (lane.focused ? 8 : 0)
    + (lane.status === 'booting' || lane.status === 'running' ? 4 : 0)
    + (lane.status === 'completed' ? 1 : 0);

  const byAgent = new Map<string, PtyLane>();
  for (const lane of lanes) {
    const key = lane.agent_type;
    const prev = byAgent.get(key);
    if (!prev || score(lane) >= score(prev)) {
      byAgent.set(key, lane);
    }
  }
  return Array.from(byAgent.values());
}

export function laneStatusSummary(lanes: PtyLane[]): string {
  const running = lanes.filter((l) => l.status === 'running' || l.status === 'booting').length;
  const completed = lanes.filter((l) => l.status === 'completed').length;
  const queued = lanes.filter((l) => l.status === 'queued').length;
  const parts = [`${lanes.length} lane${lanes.length === 1 ? '' : 's'}`];
  if (running) parts.push(`${running} running`);
  if (completed) parts.push(`${completed} completed`);
  if (queued) parts.push(`${queued} queued`);
  return parts.join(' · ');
}

export function normalizeOrchestratorDispatchText(
  text: string,
  agents: Array<{ name: string; dispatchTarget: string }>,
): string {
  if (!text.includes('@') || agents.length === 0) return text;

  let normalized = text;
  const sorted = [...agents].sort((a, b) => b.name.length - a.name.length);
  for (const agent of sorted) {
    const name = agent.name.trim();
    const target = agent.dispatchTarget.trim();
    if (!name || !target || name.toLowerCase() === target.toLowerCase()) continue;
    const pattern = new RegExp(`@${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?=\\s|$|[，,：:])`, 'gi');
    normalized = normalized.replace(pattern, `@${target}`);
  }
  return normalized;
}

export function resolveAgentTypeFromDispatchTarget(target: string): string | null {
  const needle = target.trim().toLowerCase();
  if (!needle) return null;
  for (const [agentType, display] of Object.entries(CLI_DISPLAY)) {
    if (display.toLowerCase() === needle) return agentType;
  }
  return null;
}

export function findLaneIdForAgentType(lanes: PtyLane[], agentType: string): string | null {
  const match = lanes.find(
    (lane) => lane.agent_type === agentType && lane.status !== 'completed',
  );
  return match?.lane_id ?? null;
}

/** PTY inject warmup before typing into embedded CLI TUIs (ms). */
export function resolvePtyInjectWarmupMs(
  agentType: string,
  options?: { isHandoff?: boolean; attempt?: number },
): number {
  const attempt = options?.attempt ?? 0;
  const isHandoff = options?.isHandoff ?? false;
  const isOpenCode = agentType === 'opencode-cli';

  if (isHandoff) {
    if (attempt === 0) return isOpenCode ? 3200 : 2800;
    return isOpenCode ? 1400 : 900;
  }

  if (attempt === 0) return isOpenCode ? 2800 : 1500;
  return isOpenCode ? 1200 : 600;
}
