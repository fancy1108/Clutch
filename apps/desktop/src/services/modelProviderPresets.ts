export type ModelKind = 'chat' | 'image' | 'video';

/** Built-in providers — add API key only; models ship with Clutch. */
export const BUILTIN_PROVIDER_IDS = [
  'deepseek',
  'anthropic',
  'openai',
  'google',
  'ollama',
  'agnes',
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
