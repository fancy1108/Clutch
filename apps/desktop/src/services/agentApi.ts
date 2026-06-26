import type { Agent } from '../types';
import { mergeAgentsWithBuiltin } from './builtinAgent';

import { SIDECAR_BASE as BASE } from './sidecarUrl';

export async function fetchAgents(): Promise<Agent[]> {
  const response = await fetch(`${BASE}/api/agents`);
  if (!response.ok) throw new Error(`agents fetch failed (${response.status})`);
  const body = (await response.json()) as { agents: Agent[] };
  return mergeAgentsWithBuiltin(body.agents);
}

export async function saveAgents(agents: Agent[]): Promise<void> {
  const response = await fetch(`${BASE}/api/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agents }),
  });
  if (!response.ok) throw new Error(`agents save failed (${response.status})`);
}

export interface GenerateAgentPromptResult {
  prompt: string;
  source: 'llm' | 'template';
}

export async function generateAgentPrompt(payload: {
  name: string;
  description?: string;
}): Promise<GenerateAgentPromptResult> {
  const response = await fetch(`${BASE}/api/agents/generate-prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `prompt generation failed (${response.status})`);
  }
  return response.json() as Promise<GenerateAgentPromptResult>;
}
