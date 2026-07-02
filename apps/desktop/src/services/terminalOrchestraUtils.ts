import type { PtyLane } from '@clutch/shared-types';

export const CLI_DISPLAY: Record<string, string> = {
  'claude-cli': 'Claude Code',
  'opencode-cli': 'OpenCode',
};

/** Dispatch @-mention targets shown in Orchestrator Bar picker (matches backend KNOWN_AGENTS). */
export const DISPATCH_MENTION_OPTIONS = [
  { mention: 'Claude Code', agentType: 'claude-cli' },
  { mention: 'OpenCode', agentType: 'opencode-cli' },
] as const;

export function agentDisplayName(agentType: string): string {
  return CLI_DISPLAY[agentType] ?? agentType;
}

export function mentionLabelForAgentType(agentType: string): string {
  return agentDisplayName(agentType);
}

export function formatInputMention(label: string): string {
  return `@${label} `;
}

export function computeLaneLayout(expandedCount: number): 1 | 2 | 3 {
  if (expandedCount <= 1) return 1;
  if (expandedCount === 2) return 2;
  return 3;
}

export function expandedLanes(lanes: PtyLane[]): PtyLane[] {
  return lanes.filter((lane) => !lane.collapsed && lane.status !== 'queued');
}

export function collapsedLanes(lanes: PtyLane[]): PtyLane[] {
  return lanes.filter((lane) => lane.collapsed || lane.status === 'queued');
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
