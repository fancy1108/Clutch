import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

/** UI modes after Explore→Ask merge (D27 / D54). `explore` still accepted from API as alias. */
export type PermissionMode = 'ask' | 'auto_edit' | 'plan' | 'full' | 'explore';

/**
 * Display order mirrors Cursor Agent menu: Agent → Plan → … → Ask.
 * Internal ids stay stable (`auto_edit` = Agent).
 */
export const PERMISSION_MODES: {
  id: Exclude<PermissionMode, 'explore'>;
  label: string;
  description: string;
  icon: string;
}[] = [
  {
    id: 'auto_edit',
    label: 'Agent',
    description: 'Edit files and use tools; still ask on risky shell.',
    icon: 'all_inclusive',
  },
  {
    id: 'plan',
    label: 'Plan',
    description: 'Propose a plan before editing.',
    icon: 'checklist',
  },
  {
    id: 'full',
    label: 'Full',
    description: 'Fewer confirmations — use with care.',
    icon: 'warning',
  },
  {
    id: 'ask',
    label: 'Ask',
    description: 'Conversation only — read/search, no writes or shell.',
    icon: 'chat_bubble',
  },
];

/** Normalize legacy explore → ask; default Agent (`auto_edit`). */
export function normalizePermissionMode(mode: string | null | undefined): PermissionMode {
  const raw = (mode || 'auto_edit').trim().toLowerCase();
  if (raw === 'explore') return 'ask';
  if (raw === 'auto_edit' || raw === 'plan' || raw === 'full' || raw === 'ask') {
    return raw;
  }
  return 'auto_edit';
}

export async function fetchPermissionMode(): Promise<PermissionMode> {
  const response = await sidecarFetch(`${BASE}/api/preferences/permission-mode`);
  if (!response.ok) throw new Error(`permission-mode fetch failed (${response.status})`);
  const body = (await response.json()) as { permission_mode: string };
  return normalizePermissionMode(body.permission_mode);
}

export async function savePermissionMode(mode: PermissionMode): Promise<PermissionMode> {
  const toSave = normalizePermissionMode(mode);
  const response = await sidecarFetch(`${BASE}/api/preferences/permission-mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: toSave }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `permission-mode save failed (${response.status})`);
  }
  const saved = (await response.json()) as { permission_mode: string };
  return normalizePermissionMode(saved.permission_mode);
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
