import type { Agent } from '../types';

const BASE = 'http://localhost:8123';

export async function fetchAgents(): Promise<Agent[]> {
  const response = await fetch(`${BASE}/api/agents`);
  if (!response.ok) throw new Error(`agents fetch failed (${response.status})`);
  const body = (await response.json()) as { agents: Agent[] };
  return body.agents;
}

export async function saveAgents(agents: Agent[]): Promise<void> {
  const response = await fetch(`${BASE}/api/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agents }),
  });
  if (!response.ok) throw new Error(`agents save failed (${response.status})`);
}
