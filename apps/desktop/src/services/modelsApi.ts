const BASE = 'http://localhost:8123';

export interface ModelEntry {
  id: string;
  name: string;
  provider_id: string;
  available: boolean;
  credential_source?: string | null;
  credential_source_label?: string | null;
  source_summary?: string | null;
  endpoint?: string | null;
  clutch_managed?: boolean;
  is_cc_switch?: boolean;
}

export interface ProviderEntry {
  configured: boolean;
  source: string | null;
  source_label: string | null;
  clutch_managed?: boolean;
  cc_switch_fallback_available?: boolean;
}

export interface ModelConfig {
  active_model_id: string;
  models: ModelEntry[];
  providers?: Record<string, ProviderEntry>;
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

export async function deleteProviderCredential(providerId: string): Promise<void> {
  const response = await fetch(`${BASE}/api/models/credentials/${encodeURIComponent(providerId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `credential delete failed (${response.status})`);
  }
}

export interface CcSwitchRehydrateResult {
  ok: boolean;
  message: string;
  cc_switch_found: boolean;
  models_imported: number;
  model_names?: string[];
}

export async function rehydrateCcSwitchModels(): Promise<CcSwitchRehydrateResult> {
  const response = await fetch(`${BASE}/api/models/rehydrate-cc-switch`, { method: 'POST' });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `cc-switch rehydrate failed (${response.status})`);
  }
  return response.json() as Promise<CcSwitchRehydrateResult>;
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

export const PROVIDER_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  google: 'Google',
  ollama: 'Ollama',
  custom: 'Custom',
};

const VERIFY_CACHE_KEY = 'clutch.model-verify-cache';

export type ModelVerifyState = 'ok' | 'failed';

interface ModelVerifyCacheEntry {
  state: ModelVerifyState;
  message: string;
  testedAt: string;
}

type ModelVerifyCache = Record<string, ModelVerifyCacheEntry>;

function readVerifyCache(): ModelVerifyCache {
  try {
    const raw = localStorage.getItem(VERIFY_CACHE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as ModelVerifyCache;
  } catch {
    return {};
  }
}

function writeVerifyCache(cache: ModelVerifyCache): void {
  localStorage.setItem(VERIFY_CACHE_KEY, JSON.stringify(cache));
}

export function loadModelVerifyState(): {
  verifyByModel: Record<string, ModelVerifyState>;
  verifyMessageByModel: Record<string, string>;
} {
  const verifyByModel: Record<string, ModelVerifyState> = {};
  const verifyMessageByModel: Record<string, string> = {};
  for (const [modelId, entry] of Object.entries(readVerifyCache())) {
    verifyByModel[modelId] = entry.state;
    verifyMessageByModel[modelId] = entry.message;
  }
  return { verifyByModel, verifyMessageByModel };
}

export function saveModelVerifyResult(modelId: string, ok: boolean, message: string): void {
  const cache = readVerifyCache();
  cache[modelId] = {
    state: ok ? 'ok' : 'failed',
    message,
    testedAt: new Date().toISOString(),
  };
  writeVerifyCache(cache);
}

export function removeModelVerifyResults(modelIds: Iterable<string>): void {
  const remove = new Set(modelIds);
  if (remove.size === 0) return;
  const cache = readVerifyCache();
  let changed = false;
  for (const modelId of remove) {
    if (modelId in cache) {
      delete cache[modelId];
      changed = true;
    }
  }
  if (changed) writeVerifyCache(cache);
}

export function pruneModelVerifyCache(validModelIds: Iterable<string>): void {
  const valid = new Set(validModelIds);
  const cache = readVerifyCache();
  const pruned = Object.fromEntries(Object.entries(cache).filter(([modelId]) => valid.has(modelId)));
  if (Object.keys(pruned).length !== Object.keys(cache).length) {
    writeVerifyCache(pruned);
  }
}

export function mapModelConfigToUi(config: ModelConfig) {
  const available = config.models.filter((m) => m.available);
  return {
    activeModelId: config.active_model_id,
    providers: config.providers ?? {},
    models: available.map((m) => ({
      id: m.id,
      name: m.name,
      provider: PROVIDER_LABELS[m.provider_id] ?? m.provider_id,
      providerId: m.provider_id,
      contextWindow: '—',
      temperature: 0.3,
      sourceSummary: m.source_summary ?? 'Credentials configured',
      credentialSourceLabel: m.credential_source_label ?? null,
      endpoint: m.endpoint ?? null,
      clutchManaged: Boolean(m.clutch_managed),
      isCcSwitch: Boolean(m.is_cc_switch),
    })),
    activeAvailable: available.some((m) => m.id === config.active_model_id),
  };
}
