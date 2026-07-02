export type ModelKind = 'chat' | 'image' | 'video';

/** Built-in providers — add API key only; models ship with Clutch. */
export const BUILTIN_PROVIDER_IDS = [
  'deepseek',
  'anthropic',
  'openai',
  'google',
  'ollama',
  'agnes',
  'opencode',
] as const;

/** Image / video add flow: built-in Agnes or non-built-in Custom. */
export const MEDIA_ADD_PROVIDER_IDS = ['agnes', 'custom'] as const;

export const DEFAULT_CHAT_MODEL_BY_PROVIDER: Record<string, string> = {
  deepseek: 'deepseek-v4pro',
  anthropic: 'claude-3-7-sonnet',
  openai: 'gpt-4o',
  google: 'gemini-2.5-flash',
  ollama: 'qwen2.5vl-7b',
  agnes: 'agnes-2.0-flash',
  opencode: 'opencode-deepseek-v4-flash-free',
};

export function providersForModelKind(kind: ModelKind): readonly string[] {
  if (kind === 'chat') {
    return [...BUILTIN_PROVIDER_IDS, 'custom'];
  }
  return MEDIA_ADD_PROVIDER_IDS;
}

export function defaultProviderForModelKind(kind: ModelKind): string {
  return kind === 'chat' ? 'deepseek' : 'agnes';
}

/** Built-in OpenCode Zen free chat models (refresh can extend the picker). */
export const OPENCODE_BUILTIN_MODELS = [
  {
    id: 'opencode-deepseek-v4-flash-free',
    api_model: 'deepseek-v4-flash-free',
    name: 'DeepSeek V4 Flash Free (OpenCode Zen)',
    supported: true,
  },
  {
    id: 'opencode-big-pickle',
    api_model: 'big-pickle',
    name: 'Big Pickle Free (OpenCode Zen)',
    supported: true,
  },
  {
    id: 'opencode-mimo-v2.5-free',
    api_model: 'mimo-v2.5-free',
    name: 'MiMo-V2.5 Free (OpenCode Zen)',
    supported: true,
  },
  {
    id: 'opencode-north-mini-code-free',
    api_model: 'north-mini-code-free',
    name: 'North Mini Code Free (OpenCode Zen)',
    supported: true,
  },
  {
    id: 'opencode-nemotron-3-ultra-free',
    api_model: 'nemotron-3-ultra-free',
    name: 'Nemotron 3 Ultra Free (OpenCode Zen)',
    supported: true,
  },
] as const;

export const AGNES_BUILTIN_MODEL_ID: Record<ModelKind, string> = {
  chat: 'agnes-2.0-flash',
  image: 'agnes-image-2.1-flash',
  video: 'agnes-video-v2.0',
};

export const AGNES_DEFAULTS: Record<
  ModelKind,
  { api_model: string; base_url: string; image_backend?: 'agnes'; video_backend?: 'agnes' }
> = {
  chat: {
    api_model: 'agnes-2.0-flash',
    base_url: 'https://apihub.agnes-ai.com/v1',
  },
  image: {
    api_model: 'agnes-image-2.1-flash',
    base_url: 'https://apihub.agnes-ai.com',
    image_backend: 'agnes',
  },
  video: {
    api_model: 'agnes-video-v2.0',
    base_url: 'https://apihub.agnes-ai.com',
    video_backend: 'agnes',
  },
};

export function inferImageBackend(baseUrl: string): '' | 'agnes' | 'openai_images' {
  if (baseUrl.includes('agnes-ai.com')) return 'agnes';
  return 'openai_images';
}
