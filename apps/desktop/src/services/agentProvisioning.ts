import type { Agent } from '../types';
import { fetchAgents, saveAgents } from './agentApi';
import { CLUTCH_AGENT_TYPE, agentTypeFromTool } from './agentTypes';
import { isBuiltinAgent, mergeAgentsWithBuiltin } from './builtinAgent';
import { sidecarFetch, sidecarHttpUrl } from './sidecarUrl';
import type { AiToolStatus } from './toolsApi';

export function findExistingAgentForTool(tool: AiToolStatus, existingAgents: Agent[]): Agent | null {
  const agentType = agentTypeFromTool(tool);
  if (!agentType || agentType === CLUTCH_AGENT_TYPE) return null;
  const nameLower = tool.name.trim().toLowerCase();
  return (
    existingAgents.find(
      (agent) =>
        !isBuiltinAgent(agent)
        && (agent.agentType === agentType || agent.name.trim().toLowerCase() === nameLower),
    ) ?? null
  );
}

export function buildAgentFromConnectedTool(
  tool: AiToolStatus,
  agentType: string,
  ollamaModel?: string,
): Agent {
  const name = tool.name.trim();
  const todayStr = new Date().toISOString().replace('T', ' ').substring(0, 16);
  return {
    id: `agent-${Date.now()}`,
    name,
    description: `Auto-provisioned from ${name} during onboarding.`,
    markdownDoc: `# ${name}\n\nConnected CLI agent for ${name}.`,
    lastModified: todayStr,
    avatar: `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(name)}`,
    deliverables: [],
    mcpTools: [],
    mcpServerIds: [],
    agentType,
    ollamaModel: agentType === 'ollama-cli' ? ollamaModel : undefined,
    skills: [],
  };
}

export async function fetchOllamaModelNames(): Promise<string[]> {
  const response = await sidecarFetch(sidecarHttpUrl('/api/models/ollama'));
  if (!response.ok) return [];
  const data = (await response.json()) as { ok?: boolean; models?: string[] };
  return data.ok && Array.isArray(data.models) ? data.models : [];
}

export async function ensureAgentForConnectedTool(
  tool: AiToolStatus,
  existingAgents?: Agent[],
): Promise<Agent | null> {
  const agentType = agentTypeFromTool(tool);
  if (!agentType || agentType === CLUTCH_AGENT_TYPE) return null;
  if (!tool.name.trim()) return null;

  const agents = existingAgents ?? (await fetchAgents());
  const existing = findExistingAgentForTool(tool, agents);
  if (existing) return existing;

  let ollamaModel: string | undefined;
  if (agentType === 'ollama-cli') {
    const models = await fetchOllamaModelNames();
    if (models.length === 0) return null;
    ollamaModel = models[0];
  }

  const newAgent = buildAgentFromConnectedTool(tool, agentType, ollamaModel);
  const custom = agents.filter((agent) => !isBuiltinAgent(agent));
  const normalized = mergeAgentsWithBuiltin([newAgent, ...custom]);
  await saveAgents(normalized);
  return newAgent;
}
