import { fetchPreferences } from './themeApi';
import { sidecarFetch, sidecarHttpUrl } from './sidecarUrl';

export async function fetchOnboardingState(): Promise<boolean> {
  const prefs = await fetchPreferences();
  return prefs.onboarding_completed === true;
}

export async function completeOnboarding(): Promise<void> {
  const response = await sidecarFetch(sidecarHttpUrl('/api/preferences/onboarding-complete'), {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error(`onboarding complete failed (${response.status})`);
  }
}

export async function pollHealth(): Promise<{ ok: boolean; message?: string }> {
  const response = await sidecarFetch(sidecarHttpUrl('/health'));
  if (!response.ok) {
    return { ok: false, message: `HTTP ${response.status}` };
  }
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('application/json')) {
    return { ok: false, message: 'Invalid health response' };
  }
  try {
    const body = (await response.json()) as { status?: string };
    if (body.status === 'ok') {
      return { ok: true };
    }
    return { ok: false, message: `Unexpected status: ${body.status ?? 'missing'}` };
  } catch {
    return { ok: false, message: 'Invalid health response' };
  }
}
