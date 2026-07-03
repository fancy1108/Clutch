import { agentTypeFromAgent, isCliAgentType } from './agentTypes';
import type { Agent } from '../types';
import { loadLastCliAgentId } from './terminalOrchestraUtils';

export type WorkspaceViewMode = 'chat' | 'terminal';

const STORAGE_KEY = 'clutch.workspaceViewMode';

export function loadWorkspaceViewMode(): WorkspaceViewMode {
  if (typeof localStorage === 'undefined') return 'chat';
  return localStorage.getItem(STORAGE_KEY) === 'terminal' ? 'terminal' : 'chat';
}

export function saveWorkspaceViewMode(mode: WorkspaceViewMode): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, mode);
}

/** Any connected CLI agent type (not Clutch built-in LLM) supports embedded terminal mode. */
export function isTerminalCapableAgentType(agentType: string | null | undefined): boolean {
  return isCliAgentType(agentType);
}

export function resolveCliToolForTerminal(agentType: string): string | null {
  if (!isCliAgentType(agentType)) return null;
  return agentType.trim().toLowerCase();
}

/** Fallback when only engine label is available (e.g. in-flight turn). */
export function resolveCliToolFromEngineHint(engineHint: string): string | null {
  const hint = engineHint.trim().toLowerCase();
  if (!hint) return null;

  const hintMap: Array<[string, string]> = [
    ['claude code', 'claude-cli'],
    ['claude cli', 'claude-cli'],
    ['opencode', 'opencode-cli'],
    ['open code', 'opencode-cli'],
    ['codex cli', 'codex-cli'],
    ['openai codex', 'codex-cli'],
    ['aider', 'aider-cli'],
    ['codebuddy', 'codebuddy-cli'],
    ['rivet', 'rivet-cli'],
    ['天枢', 'rivet-cli'],
    ['ollama', 'ollama-cli'],
    ['antigravity', 'antigravity-cli'],
    ['agy cli', 'antigravity-cli'],
  ];
  for (const [needle, agentType] of hintMap) {
    if (hint.includes(needle)) return agentType;
  }
  return null;
}

export function isTerminalCapableEngineHint(engineHint: string): boolean {
  return resolveCliToolFromEngineHint(engineHint) !== null;
}

/** When terminal workspace mode is active, only CLI agents are selectable in the footer. */
export function filterAgentsForTerminalWorkspace<T extends { agentType?: string; aiEngine?: string }>(
  agents: T[],
  mode: WorkspaceViewMode,
  resolveType: (agent: T) => string,
): T[] {
  if (mode !== 'terminal') return agents;
  return agents.filter((agent) => isCliAgentType(resolveType(agent)));
}

export function filterCliAgents(agents: Agent[]): Agent[] {
  return agents.filter((agent) => isCliAgentType(agentTypeFromAgent(agent)));
}

/** Last-used CLI agent, or the first configured CLI agent. */
export function resolveDefaultTerminalAgent(agents: Agent[]): Agent | undefined {
  const cliAgents = filterCliAgents(agents);
  if (cliAgents.length === 0) return undefined;
  const lastId = loadLastCliAgentId();
  return cliAgents.find((agent) => agent.id === lastId) ?? cliAgents[0];
}
