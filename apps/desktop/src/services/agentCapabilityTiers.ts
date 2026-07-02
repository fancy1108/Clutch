import { CLUTCH_AGENT_TYPE, type AgentTypeId } from './agentTypes';

export type AgentCapabilityTier = 'full' | 'readOnlyScan' | 'comingSoon';

/** Settings pages that use per-agent tabs in Phase 1+. */
export type AgentCapabilityTabId = 'clutch' | 'claude-cli' | 'opencode-cli' | 'more';

export const AGENT_CAPABILITY_TABS: Array<{
  id: AgentCapabilityTabId;
  labelKey: string;
  agentType: AgentTypeId;
}> = [
  { id: 'clutch', labelKey: 'Clutch Agent', agentType: CLUTCH_AGENT_TYPE },
  { id: 'claude-cli', labelKey: 'Claude Code', agentType: 'claude-cli' },
  { id: 'opencode-cli', labelKey: 'OpenCode', agentType: 'opencode-cli' },
  { id: 'more', labelKey: 'More', agentType: 'codex-cli' },
];

export const COMING_SOON_AGENT_TABS = [
  { id: 'codex-cli', labelKey: 'Codex', agentType: 'codex-cli' as AgentTypeId },
  { id: 'aider-cli', labelKey: 'Aider', agentType: 'aider-cli' as AgentTypeId },
  { id: 'codebuddy-cli', labelKey: 'CodeBuddy', agentType: 'codebuddy-cli' as AgentTypeId },
  { id: 'antigravity-cli', labelKey: 'Antigravity', agentType: 'antigravity-cli' as AgentTypeId },
  { id: 'rivet-cli', labelKey: 'Rivet', agentType: 'rivet-cli' as AgentTypeId },
  { id: 'ollama-cli', labelKey: 'Ollama', agentType: 'ollama-cli' as AgentTypeId },
];

const READ_ONLY_SCAN_TYPES = new Set<AgentTypeId>(['claude-cli', 'opencode-cli']);

const COMING_SOON_TYPES = new Set<AgentTypeId>([
  'codex-cli',
  'aider-cli',
  'codebuddy-cli',
  'antigravity-cli',
  'rivet-cli',
  'ollama-cli',
]);

export function getAgentCapabilityTier(agentType: AgentTypeId | string | undefined): AgentCapabilityTier {
  const normalized = (agentType ?? CLUTCH_AGENT_TYPE).trim() || CLUTCH_AGENT_TYPE;
  if (normalized === CLUTCH_AGENT_TYPE) return 'full';
  if (READ_ONLY_SCAN_TYPES.has(normalized)) return 'readOnlyScan';
  if (COMING_SOON_TYPES.has(normalized)) return 'comingSoon';
  return 'comingSoon';
}

export function settingsTabForAgentType(agentType: AgentTypeId | string | undefined): AgentCapabilityTabId | null {
  const normalized = (agentType ?? '').trim();
  if (normalized === CLUTCH_AGENT_TYPE) return 'clutch';
  if (normalized === 'claude-cli') return 'claude-cli';
  if (normalized === 'opencode-cli') return 'opencode-cli';
  return null;
}

export function capabilityPageLabel(
  page: 'models' | 'mcp' | 'skills',
  agentType: AgentTypeId | string,
): string {
  const tab = settingsTabForAgentType(agentType);
  const pageLabel =
    page === 'models' ? 'Models' : page === 'mcp' ? 'MCP Hub' : 'Skills Registry';
  if (!tab) return `Settings → ${pageLabel}`;
  const tabLabel = AGENT_CAPABILITY_TABS.find((item) => item.id === tab)?.labelKey ?? tab;
  return `Settings → ${pageLabel} (${tabLabel})`;
}
