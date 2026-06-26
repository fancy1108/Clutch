import type { Agent } from '../types';

export const AGENT_TYPE_OPTIONS = [
  { id: 'clutch', label: 'Clutch' },
  { id: 'claude-cli', label: 'Claude CLI' },
  { id: 'ollama-cli', label: 'Ollama CLI' },
  { id: 'antigravity-cli', label: 'Antigravity CLI' },
] as const;

export type AgentTypeId = (typeof AGENT_TYPE_OPTIONS)[number]['id'];

const LEGACY_ENGINE_TO_TYPE: Record<string, AgentTypeId> = {
  'configured llm': 'clutch',
  clutch: 'clutch',
  'claude code (local cli)': 'claude-cli',
  'claude code cli': 'claude-cli',
  'claude-cli': 'claude-cli',
  'claude cli': 'claude-cli',
  'antigravity cli': 'antigravity-cli',
  'antigravity-cli': 'antigravity-cli',
  'agy-cli': 'antigravity-cli',
  ollama: 'ollama-cli',
  'ollama-cli': 'ollama-cli',
  'ollama (cli)': 'ollama-cli',
};

export function agentTypeFromAgent(agent: Pick<Agent, 'agentType' | 'aiEngine'> | null | undefined): AgentTypeId {
  if (!agent) return 'clutch';
  const explicit = agent.agentType?.trim();
  if (explicit && AGENT_TYPE_OPTIONS.some((item) => item.id === explicit)) {
    return explicit as AgentTypeId;
  }
  const legacy = agent.aiEngine?.trim().toLowerCase() ?? '';
  return LEGACY_ENGINE_TO_TYPE[legacy] ?? 'clutch';
}

export function isClutchAgentType(agent: Pick<Agent, 'agentType' | 'aiEngine' | 'builtin' | 'id'> | null | undefined): boolean {
  return agentTypeFromAgent(agent) === 'clutch';
}

export function agentTypeLabel(agentType: AgentTypeId): string {
  return AGENT_TYPE_OPTIONS.find((item) => item.id === agentType)?.label ?? agentType;
}
