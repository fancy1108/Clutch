import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

export interface ModelEntry {
  id: string;
  name: string;
  provider_id: string;
  model_kind?: 'chat' | 'image' | 'video';
  image_backend?: string;
  available: boolean;
  credential_source?: string | null;
  credential_source_label?: string | null;
  source_summary?: string | null;
  endpoint?: string | null;
  clutch_managed?: boolean;
  is_cc_switch?: boolean;
  is_custom?: boolean;
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

export type ModelsConfigErrorKind = 'unauthorized' | 'unreachable' | 'server' | 'other';

export class ModelsConfigError extends Error {
  readonly kind: ModelsConfigErrorKind;

  constructor(kind: ModelsConfigErrorKind, message: string) {
    super(message);
    this.name = 'ModelsConfigError';
    this.kind = kind;
  }
}

export async function fetchModelsConfig(): Promise<ModelConfig> {
  let response: Response;
  try {
    response = await sidecarFetch(`${BASE}/api/models/config`, { cache: 'no-store' });
  } catch {
    throw new ModelsConfigError('unreachable', 'sidecar unreachable');
  }
  if (response.status === 401) {
    throw new ModelsConfigError('unauthorized', 'sidecar unauthorized');
  }
  if (response.status >= 500) {
    throw new ModelsConfigError('server', `sidecar server error (${response.status})`);
  }
  if (!response.ok) {
    throw new ModelsConfigError('other', `models config failed (${response.status})`);
  }
  return response.json() as Promise<ModelConfig>;
}

export async function saveModelsConfig(payload: {
  active_model_id?: string;
  provider_id?: string;
  api_key?: string;
}): Promise<void> {
  const response = await sidecarFetch(`${BASE}/api/models/config`, {
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
  const response = await sidecarFetch(`${BASE}/api/models/credentials/${encodeURIComponent(providerId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `credential delete failed (${response.status})`);
  }
}

export async function fetchProviderApiKey(providerId: string): Promise<string | null> {
  const response = await sidecarFetch(
    `${BASE}/api/models/credentials/${encodeURIComponent(providerId)}`,
    { cache: 'no-store' },
  );
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new Error(`credential fetch failed (${response.status})`);
  }
  const body = (await response.json()) as { api_key?: string; configured?: boolean };
  return body.configured && body.api_key ? body.api_key : null;
}

export interface CcSwitchRehydrateResult {
  ok: boolean;
  message: string;
  cc_switch_found: boolean;
  models_imported: number;
  model_names?: string[];
}

export async function rehydrateCcSwitchModels(): Promise<CcSwitchRehydrateResult> {
  const response = await sidecarFetch(`${BASE}/api/models/rehydrate-cc-switch`, { method: 'POST' });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `cc-switch rehydrate failed (${response.status})`);
  }
  return response.json() as Promise<CcSwitchRehydrateResult>;
}

export async function testModelConnection(modelId: string): Promise<ModelTestResult> {
  const response = await sidecarFetch(`${BASE}/api/models/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId }),
  });
  if (!response.ok) throw new Error(`model test failed (${response.status})`);
  return response.json() as Promise<ModelTestResult>;
}

export interface AddCustomImageModelInput {
  name: string;
  api_model: string;
  base_url: string;
  provider_id?: string;
  image_backend?: '' | 'agnes' | 'openai_images';
  api_key?: string;
}

export interface AddCustomChatModelInput {
  name: string;
  api_model: string;
  base_url: string;
  provider_id?: string;
  api_key?: string;
}

export async function addCustomChatModel(
  input: AddCustomChatModelInput,
): Promise<{ model_id: string; config: ModelConfig }> {
  const response = await sidecarFetch(`${BASE}/api/models/custom/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `add chat model failed (${response.status})`);
  }
  return response.json() as Promise<{ model_id: string; config: ModelConfig }>;
}

export interface AddCustomVideoModelInput {
  name: string;
  api_model: string;
  base_url: string;
  provider_id?: string;
  video_backend?: 'agnes';
  api_key?: string;
}

export async function addCustomImageModel(
  input: AddCustomImageModelInput,
): Promise<{ model_id: string; config: ModelConfig }> {
  const response = await sidecarFetch(`${BASE}/api/models/custom/image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `add image model failed (${response.status})`);
  }
  return response.json() as Promise<{ model_id: string; config: ModelConfig }>;
}

export async function addCustomVideoModel(
  input: AddCustomVideoModelInput,
): Promise<{ model_id: string; config: ModelConfig }> {
  const response = await sidecarFetch(`${BASE}/api/models/custom/video`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `add video model failed (${response.status})`);
  }
  return response.json() as Promise<{ model_id: string; config: ModelConfig }>;
}

export interface UpdateCustomModelInput {
  name: string;
  api_model: string;
  base_url: string;
  api_key?: string;
}

export async function updateCustomModel(
  modelId: string,
  input: UpdateCustomModelInput,
): Promise<ModelConfig> {
  const response = await sidecarFetch(`${BASE}/api/models/custom/${encodeURIComponent(modelId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `update custom model failed (${response.status})`);
  }
  const body = (await response.json()) as { config: ModelConfig };
  return body.config;
}

export async function deleteCustomModel(modelId: string): Promise<ModelConfig> {
  const response = await sidecarFetch(`${BASE}/api/models/custom/${encodeURIComponent(modelId)}`, {
    method: 'DELETE',
    cache: 'no-store',
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `delete custom model failed (${response.status})`);
  }
  const body = (await response.json()) as { config: ModelConfig };
  return body.config;
}

export interface OpencodeZenModelOption {
  id: string;
  api_model: string;
  name: string;
  supported: boolean;
}

export async function fetchOpencodeZenModels(): Promise<{
  ok: boolean;
  models: OpencodeZenModelOption[];
  message?: string;
}> {
  const response = await sidecarFetch(`${BASE}/api/models/opencode-zen/list`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (!response.ok) {
    throw new Error(`OpenCode Zen model list failed (${response.status})`);
  }
  return response.json() as Promise<{
    ok: boolean;
    models: OpencodeZenModelOption[];
    message?: string;
  }>;
}

export const PROVIDER_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  anthropic: 'Anthropic',
  openai: 'OpenAI',
  google: 'Google',
  ollama: 'Ollama',
  agnes: 'Agnes',
  opencode: 'OpenCode Zen',
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

export const MODEL_KIND_ORDER: Record<string, number> = { chat: 0, image: 1, video: 2 };

export function sortModelsByKind<T extends { modelKind?: string; name: string }>(models: T[]): T[] {
  return [...models].sort((a, b) => {
    const kindA = MODEL_KIND_ORDER[a.modelKind ?? 'chat'] ?? 0;
    const kindB = MODEL_KIND_ORDER[b.modelKind ?? 'chat'] ?? 0;
    if (kindA !== kindB) return kindA - kindB;
    return a.name.localeCompare(b.name);
  });
}

export function modelKindMenuSuffix(modelKind?: string): string {
  if (modelKind === 'image') return ' (image)';
  if (modelKind === 'video') return ' (video)';
  return '';
}

/** Prefer DeepSeek V4 Pro when available; otherwise first available chat (non-image) model. */
export function resolveDefaultTextModelId(config: ModelConfig): string {
  const chatModels = config.models.filter(
    (model) => model.available && !['image', 'video'].includes(model.model_kind ?? 'chat'),
  );
  const preferred = chatModels.find((model) => model.id === DEFAULT_TEXT_MODEL_ID);
  return preferred?.id ?? chatModels[0]?.id ?? config.active_model_id;
}

export function mapModelConfigToUi(config: ModelConfig) {
  const visible = config.models.filter((m) => m.available || m.is_custom);
  const available = visible.filter((m) => m.available);
  return {
    activeModelId: config.active_model_id,
    providers: config.providers ?? {},
    models: sortModelsByKind(visible.map((m) => ({
      id: m.id,
      name: m.name,
      provider: PROVIDER_LABELS[m.provider_id] ?? m.provider_id,
      providerId: m.provider_id,
      modelKind: m.model_kind ?? 'chat',
      imageBackend: m.image_backend ?? '',
      available: m.available,
      contextWindow: '—',
      temperature: 0.3,
      sourceSummary: m.available
        ? (m.source_summary ?? 'Credentials configured')
        : 'Add an API key for this provider to enable this model.',
      credentialSourceLabel: m.credential_source_label ?? null,
      endpoint: m.endpoint ?? null,
      clutchManaged: Boolean(m.clutch_managed),
      isCcSwitch: Boolean(m.is_cc_switch),
      isCustom: Boolean(m.is_custom),
    }))),
    activeAvailable: available.some((m) => m.id === config.active_model_id),
  };
}
