import type { Agent } from '../types';
import type { AiToolStatus } from './toolsApi';

export const CLUTCH_AGENT_TYPE = 'clutch' as const;

/** Runtime agent type id (clutch or any registered CLI routing key from the sidecar). */
export type AgentTypeId = string;

export type AgentTypeOption = { id: AgentTypeId; label: string };

const LEGACY_ENGINE_TO_TYPE: Record<string, AgentTypeId> = {
  'configured llm': CLUTCH_AGENT_TYPE,
  clutch: CLUTCH_AGENT_TYPE,
  'claude code (local cli)': 'claude-cli',
  'claude code cli': 'claude-cli',
  'claude-cli': 'claude-cli',
  'claude cli': 'claude-cli',
  'antigravity cli': 'antigravity-cli',
  'antigravity-cli': 'antigravity-cli',
  'agy-cli': 'antigravity-cli',
  'codex-cli': 'codex-cli',
  codex: 'codex-cli',
  'codex cli': 'codex-cli',
  'openai codex cli': 'codex-cli',
  ollama: 'ollama-cli',
  'ollama-cli': 'ollama-cli',
  'ollama (cli)': 'ollama-cli',
  aider: 'aider-cli',
  'aider-cli': 'aider-cli',
  'aider (cli)': 'aider-cli',
  'opencode-cli': 'opencode-cli',
  opencode: 'opencode-cli',
  'open code cli': 'opencode-cli',
  'codebuddy-cli': 'codebuddy-cli',
  codebuddy: 'codebuddy-cli',
  'codebuddy cli': 'codebuddy-cli',
  cbc: 'codebuddy-cli',
};

const AGENT_TYPE_DISPLAY_LABELS: Record<string, string> = {
  'claude-cli': 'Claude CLI',
  'ollama-cli': 'Ollama',
  'antigravity-cli': 'Antigravity CLI',
  'codex-cli': 'Codex CLI',
  'aider-cli': 'Aider CLI',
  'opencode-cli': 'OpenCode CLI',
  'codebuddy-cli': 'CodeBuddy CLI',
};

const LEGACY_TYPE_LABELS: Record<string, string> = {
  [CLUTCH_AGENT_TYPE]: 'Clutch',
  ...AGENT_TYPE_DISPLAY_LABELS,
};

function displayLabelForTool(tool: AiToolStatus, agentType: string): string {
  const base = AGENT_TYPE_DISPLAY_LABELS[agentType] ?? tool.name?.trim() ?? agentTypeLabel(agentType);
  if (tool.connected && !tool.registered) {
    return `${base} (needs Auto-configure)`;
  }
  return base;
}

export function agentTypeFromTool(tool: AiToolStatus): string | null {
  const fromApi = tool.agentType?.trim();
  if (fromApi) return fromApi;
  const fromId = LEGACY_ENGINE_TO_TYPE[tool.id.trim().toLowerCase()];
  if (fromId && fromId !== CLUTCH_AGENT_TYPE) return fromId;
  return null;
}

/** Agent types available for new agents: Clutch + connected CLI tools (registered or pending configure). */
export function agentTypeOptionsFromTools(tools: AiToolStatus[]): AgentTypeOption[] {
  const options: AgentTypeOption[] = [{ id: CLUTCH_AGENT_TYPE, label: 'Clutch' }];
  const seen = new Set<string>([CLUTCH_AGENT_TYPE]);

  for (const tool of tools) {
    if (!tool.connected) continue;
    const agentType = agentTypeFromTool(tool);
    if (!agentType || seen.has(agentType)) continue;
    seen.add(agentType);
    options.push({ id: agentType, label: displayLabelForTool(tool, agentType) });
  }
  return options;
}

/** Include the current type when editing an agent whose tool is no longer connected. */
export function buildSelectableAgentTypeOptions(
  tools: AiToolStatus[],
  currentType?: AgentTypeId,
): AgentTypeOption[] {
  const options = agentTypeOptionsFromTools(tools);
  const current = currentType?.trim();
  if (!current || current === CLUTCH_AGENT_TYPE || options.some((item) => item.id === current)) {
    return options;
  }
  return [...options, { id: current, label: agentTypeLabel(current, tools) }];
}

export function agentTypeFromAgent(agent: Pick<Agent, 'agentType' | 'aiEngine'> | null | undefined): AgentTypeId {
  if (!agent) return CLUTCH_AGENT_TYPE;
  const explicit = agent.agentType?.trim();
  if (explicit) return explicit;
  const legacy = agent.aiEngine?.trim().toLowerCase() ?? '';
  return LEGACY_ENGINE_TO_TYPE[legacy] ?? CLUTCH_AGENT_TYPE;
}

export function isClutchAgentType(agent: Pick<Agent, 'agentType' | 'aiEngine' | 'builtin' | 'id'> | null | undefined): boolean {
  return agentTypeFromAgent(agent) === CLUTCH_AGENT_TYPE;
}

export function agentTypeLabel(agentType: AgentTypeId, tools?: AiToolStatus[]): string {
  if (agentType === CLUTCH_AGENT_TYPE) return 'Clutch';
  if (AGENT_TYPE_DISPLAY_LABELS[agentType]) return AGENT_TYPE_DISPLAY_LABELS[agentType];
  const matched = tools?.find(
    (tool) => tool.agentType === agentType || tool.id === agentType,
  );
  if (matched?.name) return matched.name;
  return LEGACY_TYPE_LABELS[agentType] ?? agentType;
}
