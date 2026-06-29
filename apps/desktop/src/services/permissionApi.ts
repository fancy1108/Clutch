import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

export type PermissionMode = 'ask' | 'auto_edit' | 'plan' | 'full';

export const PERMISSION_MODES: {
  id: PermissionMode;
  label: string;
  description: string;
  icon: string;
}[] = [
  {
    id: 'ask',
    label: 'Ask before changes',
    description: 'Ask before file changes.',
    icon: 'front_hand',
  },
  {
    id: 'auto_edit',
    label: 'Edit automatically',
    description: 'Edit files automatically.',
    icon: 'verified_user',
  },
  {
    id: 'plan',
    label: 'Plan mode',
    description: 'Plan before editing.',
    icon: 'edit_note',
  },
  {
    id: 'full',
    label: 'Full access',
    description: 'Run with fewer confirmations.',
    icon: 'warning',
  },
];

export async function fetchPermissionMode(): Promise<PermissionMode> {
  const response = await sidecarFetch(`${BASE}/api/preferences/permission-mode`);
  if (!response.ok) throw new Error(`permission-mode fetch failed (${response.status})`);
  const body = (await response.json()) as { permission_mode: string };
  return (body.permission_mode as PermissionMode) || 'ask';
}

export async function savePermissionMode(mode: PermissionMode): Promise<PermissionMode> {
  const response = await sidecarFetch(`${BASE}/api/preferences/permission-mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `permission-mode save failed (${response.status})`);
  }
  const saved = (await response.json()) as { permission_mode: string };
  return (saved.permission_mode as PermissionMode) || 'ask';
}
