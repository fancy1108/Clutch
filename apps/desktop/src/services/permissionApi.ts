import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

export type PermissionMode = 'ask' | 'auto_edit' | 'explore' | 'plan' | 'full';


/** Display order: safer → more autonomous (mode pill menu). */
export const PERMISSION_MODES: {
  id: PermissionMode;
  label: string;
  description: string;
  icon: string;
}[] = [
  {
    id: 'explore',
    label: 'Explore',
    description: 'Read and search only — no writes.',
    icon: 'visibility',
  },
  {
    id: 'plan',
    label: 'Plan',
    description: 'Propose a plan before editing.',
    icon: 'edit_note',
  },
  {
    id: 'ask',
    label: 'Ask',
    description: 'Ask before file changes or risky tools.',
    icon: 'front_hand',
  },
  {
    id: 'auto_edit',
    label: 'Edit',
    description: 'Edit files automatically; still ask on risky shell.',
    icon: 'verified_user',
  },
  {
    id: 'full',
    label: 'Full',
    description: 'Fewer confirmations — use with care.',
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

export async function fetchStrictSandbox(): Promise<boolean> {
  const response = await sidecarFetch(`${BASE}/api/preferences/strict-sandbox`);
  if (!response.ok) throw new Error(`strict-sandbox fetch failed (${response.status})`);
  const body = (await response.json()) as { strict_sandbox: boolean };
  return Boolean(body.strict_sandbox);
}

export async function saveStrictSandbox(enabled: boolean): Promise<boolean> {
  const response = await sidecarFetch(`${BASE}/api/preferences/strict-sandbox`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `strict-sandbox save failed (${response.status})`);
  }
  const saved = (await response.json()) as { strict_sandbox: string };
  return saved.strict_sandbox === 'true';
}

export async function fetchAllowNetwork(): Promise<boolean> {
  const response = await sidecarFetch(`${BASE}/api/preferences/allow-network`);
  if (!response.ok) throw new Error(`allow-network fetch failed (${response.status})`);
  const body = (await response.json()) as { allow_network: boolean };
  return Boolean(body.allow_network);
}

export async function saveAllowNetwork(enabled: boolean): Promise<boolean> {
  const response = await sidecarFetch(`${BASE}/api/preferences/allow-network`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `allow-network save failed (${response.status})`);
  }
  const saved = (await response.json()) as { allow_network: string };
  return saved.allow_network === 'true';
}

export interface CrossSessionMemoryEntry {
  id: string;
  text: string;
  created_at?: number;
}

export async function fetchCrossSessionMemory(): Promise<{
  enabled: boolean;
  entries: CrossSessionMemoryEntry[];
}> {
  const response = await sidecarFetch(`${BASE}/api/preferences/cross-session-memory`);
  if (!response.ok) throw new Error(`cross-session-memory fetch failed (${response.status})`);
  return (await response.json()) as { enabled: boolean; entries: CrossSessionMemoryEntry[] };
}

export async function saveCrossSessionMemory(enabled: boolean): Promise<boolean> {
  const response = await sidecarFetch(`${BASE}/api/preferences/cross-session-memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `cross-session-memory save failed (${response.status})`);
  }
  const saved = (await response.json()) as { cross_session_memory_enabled: string };
  return saved.cross_session_memory_enabled === 'true';
}

export async function clearCrossSessionMemory(): Promise<number> {
  const response = await sidecarFetch(`${BASE}/api/preferences/cross-session-memory/clear`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`cross-session-memory clear failed (${response.status})`);
  const body = (await response.json()) as { cleared: number };
  return body.cleared ?? 0;
}
