const BASE = 'http://localhost:8123';

export const THEME_PRESET_IDS = ['pristine-light', 'nordic-frost', 'amber-warm'] as const;
export type ThemePresetId = (typeof THEME_PRESET_IDS)[number];
export type AppLanguage = 'en' | 'zh';

export interface UserPreferences {
  active_theme_id: ThemePresetId;
  active_language: AppLanguage;
}

export async function fetchPreferences(): Promise<UserPreferences> {
  const response = await fetch(`${BASE}/api/preferences`);
  if (!response.ok) throw new Error(`preferences failed (${response.status})`);
  const body = (await response.json()) as UserPreferences;
  const themeId = (THEME_PRESET_IDS as readonly string[]).includes(body.active_theme_id)
    ? body.active_theme_id
    : 'pristine-light';
  const language = body.active_language === 'zh' ? 'zh' : 'en';
  return { active_theme_id: themeId, active_language: language };
}

export async function fetchThemePreference(): Promise<ThemePresetId> {
  const prefs = await fetchPreferences();
  return prefs.active_theme_id;
}

export async function saveThemePreference(themeId: ThemePresetId): Promise<ThemePresetId> {
  const response = await fetch(`${BASE}/api/preferences/theme`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ theme_id: themeId }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `theme save failed (${response.status})`);
  }
  const saved = (await response.json()) as UserPreferences;
  return saved.active_theme_id;
}

export async function fetchLanguagePreference(): Promise<AppLanguage> {
  const response = await fetch(`${BASE}/api/preferences/language`);
  if (!response.ok) throw new Error(`language preference failed (${response.status})`);
  const body = (await response.json()) as { active_language?: string };
  return body.active_language === 'zh' ? 'zh' : 'en';
}

export async function saveLanguagePreference(language: AppLanguage): Promise<AppLanguage> {
  const response = await fetch(`${BASE}/api/preferences/language`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ language }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `language save failed (${response.status})`);
  }
  const saved = (await response.json()) as UserPreferences;
  return saved.active_language;
}
