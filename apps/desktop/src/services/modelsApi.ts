const BASE = 'http://localhost:8123';

export interface ModelEntry {
  id: string;
  name: string;
  provider_id: string;
  available: boolean;
  credential_source?: string | null;
  credential_source_label?: string | null;
}

export interface ModelConfig {
  active_model_id: string;
  models: ModelEntry[];
  providers?: Record<
    string,
    { configured: boolean; source: string | null; source_label: string | null }
  >;
}

export interface ModelTestResult {
  ok: boolean;
  model_id: string;
  message: string;
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
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `models save failed (${response.status})`);
  }
}

export async function testModelConnection(modelId: string): Promise<ModelTestResult> {
  const response = await fetch(`${BASE}/api/models/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId }),
  });
  if (!response.ok) throw new Error(`model test failed (${response.status})`);
  return response.json() as Promise<ModelTestResult>;
}

export async function fetchMcpStatus(): Promise<{
  filesystem: { connected: boolean; tools: number; workspace_path?: string | null };
}> {
  const response = await fetch(`${BASE}/api/mcp/status`);
  if (!response.ok) throw new Error(`mcp status failed (${response.status})`);
  return response.json() as Promise<{ filesystem: { connected: boolean; tools: number; workspace_path?: string | null } }>;
}

export const PROVIDER_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  google: 'Google',
  ollama: 'Ollama',
  custom: 'Custom',
};

export function mapModelConfigToUi(config: ModelConfig) {
  const available = config.models.filter((m) => m.available);
  return {
    activeModelId: config.active_model_id,
    models: available.map((m) => ({
      id: m.id,
      name: m.name,
      provider: PROVIDER_LABELS[m.provider_id] ?? m.provider_id,
      providerId: m.provider_id,
      contextWindow: '—',
      temperature: 0.3,
      description: m.credential_source_label
        ? `Credential source: ${m.credential_source_label}`
        : 'Credential source unknown.',
      credentialSourceLabel: m.credential_source_label ?? null,
    })),
    activeAvailable: available.some((m) => m.id === config.active_model_id),
  };
}
