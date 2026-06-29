import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

export interface ScannedSkill {
  key: string;
  label: string;
  source: string;
  isActiveGlobally: boolean;
  desc: string;
}

export interface SkillsRegistryState {
  mounted_directories: string[];
  skills: ScannedSkill[];
}

export async function fetchSkillsRegistry(): Promise<SkillsRegistryState> {
  const response = await sidecarFetch(`${BASE}/api/skills`);
  if (!response.ok) throw new Error(`skills registry failed (${response.status})`);
  return response.json() as Promise<SkillsRegistryState>;
}

export async function mountSkillsDirectory(path: string): Promise<SkillsRegistryState> {
  const response = await sidecarFetch(`${BASE}/api/skills/mount`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `skills mount failed (${response.status})`);
  }
  return response.json() as Promise<SkillsRegistryState>;
}

export async function unmountSkillsDirectory(path: string): Promise<SkillsRegistryState> {
  const response = await sidecarFetch(`${BASE}/api/skills/unmount`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!response.ok) throw new Error(`skills unmount failed (${response.status})`);
  return response.json() as Promise<SkillsRegistryState>;
}

export async function toggleSkillActive(key: string, isActive: boolean): Promise<SkillsRegistryState> {
  const response = await sidecarFetch(`${BASE}/api/skills/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, is_active: isActive }),
  });
  if (!response.ok) throw new Error(`skills toggle failed (${response.status})`);
  return response.json() as Promise<SkillsRegistryState>;
}

export function notifySkillsUpdated(): void {
  window.dispatchEvent(new Event('clutch-skills-updated'));
}
