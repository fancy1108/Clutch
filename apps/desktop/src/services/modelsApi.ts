const BASE = 'http://localhost:8123';

export interface ModelConfig {
  active_model_id: string;
  models: Array<{ id: string; name: string; provider_id: string }>;
}

export async function fetchModelsConfig(): Promise<ModelConfig> {
  const response = await fetch(`${BASE}/api/models/config`);
  if (!response.ok) throw new Error(`models config failed (${response.status})`);
  return response.json() as Promise<ModelConfig>;
}

export async function saveModelsConfig(payload: {
  active_model_id?: string;
  provider_id?: string;
  api_key?: string;
}): Promise<void> {
  const response = await fetch(`${BASE}/api/models/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`models save failed (${response.status})`);
}

export async function fetchMcpStatus(): Promise<{ filesystem: { connected: boolean; tools: number } }> {
  const response = await fetch(`${BASE}/api/mcp/status`);
  if (!response.ok) throw new Error(`mcp status failed (${response.status})`);
  return response.json() as Promise<{ filesystem: { connected: boolean; tools: number } }>;
}
