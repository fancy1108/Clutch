/**
 * D51 — Chat ↔ Terminal sync helpers.
 * Click a Shell / execute tool step → switch Terminal view, focus lane, highlight log/dispatch.
 */

import type { DispatchLogEntry, ToolStep } from '../types';

export type ChatTerminalSyncTarget = {
  laneId: string;
  logIndex: number | null;
  dispatchEntryId: string | null;
};

function shortTool(tool: string): string {
  if (tool.includes('__')) return tool.split('__').slice(1).join('__') || tool;
  return tool;
}

/** Extract a searchable command / focus fragment from a tool step. */
export function stepSearchNeedle(step: ToolStep): string {
  const detail = (step.detail || '').trim();
  // First line is usually the target (URL / path / query) before result preview.
  const primary = detail.split('\n').find((line) => line.trim() && !line.startsWith('──'))?.trim() || '';
  if (primary.startsWith('{')) {
    try {
      const parsed = JSON.parse(primary) as Record<string, unknown>;
      const command = parsed.command ?? parsed.cmd;
      if (typeof command === 'string' && command.trim()) return command.trim();
      const url = parsed.url ?? parsed.uri ?? parsed.href;
      if (typeof url === 'string' && url.trim()) return url.trim();
      const path = parsed.path ?? parsed.file_path;
      if (typeof path === 'string' && path.trim()) return path.trim();
      const query = parsed.query ?? parsed.pattern ?? parsed.q;
      if (typeof query === 'string' && query.trim()) return query.trim();
    } catch {
      /* fall through */
    }
  }
  if (primary && (primary.startsWith('http') || primary.includes('/') || primary.length >= 4)) {
    return primary;
  }
  const title = step.title.trim();
  // Titles like "Run echo hi" / "Fetched host/path" → prefer the tail after the verb.
  const runMatch = /^(?:Run|Shell|Exec|Fetched|Searched|Read|List|Edit)\s+(.+)$/i.exec(title);
  if (runMatch?.[1]) return runMatch[1].replace(/^[“"]|[”"]$/g, '').trim();
  return title || shortTool(step.tool);
}

/** Any Chat tool trail step can jump to its matching `[CHAT] Step …` audit line. */
export function isTerminalSyncableStep(step: ToolStep): boolean {
  return Boolean(step.tool?.trim());
}

export function resolveSyncLaneId(state: {
  focused_lane_id?: string | null;
  pty_lanes?: Array<{ lane_id: string; focused?: boolean; status?: string }>;
}): string {
  const focus = (state.focused_lane_id || '').trim();
  if (focus) return focus === 'primary' ? 'lane_primary' : focus;
  const lanes = state.pty_lanes ?? [];
  const focused = lanes.find((lane) => lane.focused);
  if (focused?.lane_id) {
    return focused.lane_id === 'primary' ? 'lane_primary' : focused.lane_id;
  }
  const live = lanes.find((lane) => lane.status && lane.status !== 'completed');
  if (live?.lane_id) {
    return live.lane_id === 'primary' ? 'lane_primary' : live.lane_id;
  }
  if (lanes[0]?.lane_id) {
    return lanes[0].lane_id === 'primary' ? 'lane_primary' : lanes[0].lane_id;
  }
  return 'lane_primary';
}

/** Find the best matching terminal_logs line for this step (latest match wins). */
export function findLogIndexForStep(logs: string[], step: ToolStep): number | null {
  if (!logs.length) return null;
  const tool = shortTool(step.tool).toLowerCase();
  const needle = stepSearchNeedle(step).toLowerCase();
  let best: number | null = null;
  for (let i = 0; i < logs.length; i += 1) {
    const line = logs[i];
    if (!/\[(?:CHAT|MCP)\]\s+Step\s+\d+/i.test(line)) continue;
    const lower = line.toLowerCase();
    const toolHit = tool ? lower.includes(tool) : false;
    const needleHit = needle.length >= 2 && lower.includes(needle.slice(0, Math.min(needle.length, 80)));
    if (toolHit || needleHit) best = i;
  }
  return best;
}

/** Match a dispatch_log entry whose prompt mentions the step command (latest wins). */
export function findDispatchEntryIdForStep(
  entries: DispatchLogEntry[],
  step: ToolStep,
): string | null {
  const needle = stepSearchNeedle(step).toLowerCase();
  if (!needle || needle.length < 2) return null;
  let best: string | null = null;
  for (const entry of entries) {
    const prompt = (entry.prompt || '').toLowerCase();
    if (prompt.includes(needle.slice(0, Math.min(needle.length, 80)))) {
      best = entry.id;
    }
  }
  return best;
}

export function resolveChatTerminalSyncTarget(
  step: ToolStep,
  state: {
    focused_lane_id?: string | null;
    pty_lanes?: Array<{ lane_id: string; focused?: boolean; status?: string }>;
    terminal_logs?: string[];
    dispatch_log?: DispatchLogEntry[];
  },
): ChatTerminalSyncTarget {
  return {
    laneId: resolveSyncLaneId(state),
    logIndex: findLogIndexForStep(state.terminal_logs ?? [], step),
    dispatchEntryId: findDispatchEntryIdForStep(state.dispatch_log ?? [], step),
  };
}
