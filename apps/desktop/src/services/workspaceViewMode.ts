export type WorkspaceViewMode = 'chat' | 'terminal';

const STORAGE_KEY = 'clutch.workspaceViewMode';

/** Agent types that support embedded interactive CLI terminal mode. */
export const TERMINAL_CAPABLE_AGENT_TYPES = new Set(['claude-cli', 'opencode-cli']);

export function loadWorkspaceViewMode(): WorkspaceViewMode {
  if (typeof localStorage === 'undefined') return 'chat';
  return localStorage.getItem(STORAGE_KEY) === 'terminal' ? 'terminal' : 'chat';
}

export function saveWorkspaceViewMode(mode: WorkspaceViewMode): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, mode);
}

export function isTerminalCapableAgentType(agentType: string | null | undefined): boolean {
  if (!agentType) return false;
  return TERMINAL_CAPABLE_AGENT_TYPES.has(agentType.trim().toLowerCase());
}

export function resolveCliToolForTerminal(agentType: string): string | null {
  const key = agentType.trim().toLowerCase();
  if (key === 'claude-cli' || key === 'opencode-cli') return key;
  return null;
}

/** Fallback when only engine label is available (e.g. in-flight turn). */
export function resolveCliToolFromEngineHint(engineHint: string): string | null {
  const hint = engineHint.trim().toLowerCase();
  if (hint.includes('opencode cli') || hint === 'opencode cli') return 'opencode-cli';
  if (hint.includes('claude cli') || hint === 'claude cli') return 'claude-cli';
  return null;
}

export function isTerminalCapableEngineHint(engineHint: string): boolean {
  return resolveCliToolFromEngineHint(engineHint) !== null;
}

/** When terminal workspace mode is active, only Claude CLI and OpenCode CLI agents are selectable. */
export function filterAgentsForTerminalWorkspace<T extends { agentType?: string; aiEngine?: string }>(
  agents: T[],
  mode: WorkspaceViewMode,
  resolveType: (agent: T) => string,
): T[] {
  if (mode !== 'terminal') return agents;
  return agents.filter((agent) => isTerminalCapableAgentType(resolveType(agent)));
}
