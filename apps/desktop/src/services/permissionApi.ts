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

export async function fetchDefaultWorkspaceId(): Promise<string> {
  const response = await sidecarFetch(`${BASE}/api/preferences/default-workspace`);
  if (!response.ok) throw new Error(`default-workspace fetch failed (${response.status})`);
  const body = (await response.json()) as { workspace_id?: string };
  return String(body.workspace_id ?? '');
}

export async function saveDefaultWorkspaceId(workspaceId: string): Promise<string> {
  const response = await sidecarFetch(`${BASE}/api/preferences/default-workspace`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workspace_id: workspaceId }),
  });
  if (!response.ok) throw new Error(`default-workspace save failed (${response.status})`);
  const saved = (await response.json()) as { default_workspace_id?: string };
  return String(saved.default_workspace_id ?? workspaceId);
}

export async function fetchHighRiskConfirm(): Promise<boolean> {
  const response = await sidecarFetch(`${BASE}/api/preferences/high-risk-confirm`);
  if (!response.ok) throw new Error(`high-risk-confirm fetch failed (${response.status})`);
  const body = (await response.json()) as { high_risk_confirm: boolean };
  return Boolean(body.high_risk_confirm);
}

export async function saveHighRiskConfirm(enabled: boolean): Promise<boolean> {
  const response = await sidecarFetch(`${BASE}/api/preferences/high-risk-confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) throw new Error(`high-risk-confirm save failed (${response.status})`);
  const saved = (await response.json()) as { high_risk_confirm: string };
  return saved.high_risk_confirm === 'true';
}

export type LocalTrustState = {
  untrusted_confirm: boolean;
  trusted_mcp_ids: string[];
  trusted_workflow_ids: string[];
};

export async function fetchLocalTrust(): Promise<LocalTrustState> {
  const response = await sidecarFetch(`${BASE}/api/preferences/local-trust`);
  if (!response.ok) throw new Error(`local-trust fetch failed (${response.status})`);
  return (await response.json()) as LocalTrustState;
}

export async function saveUntrustedConfirm(enabled: boolean): Promise<boolean> {
  const response = await sidecarFetch(`${BASE}/api/preferences/untrusted-confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!response.ok) throw new Error(`untrusted-confirm save failed (${response.status})`);
  const saved = (await response.json()) as { untrusted_confirm: string };
  return saved.untrusted_confirm === 'true';
}

export async function rememberTrustedId(kind: 'mcp' | 'workflow', itemId: string): Promise<void> {
  const response = await sidecarFetch(`${BASE}/api/preferences/local-trust`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, item_id: itemId }),
  });
  if (!response.ok) throw new Error(`local-trust save failed (${response.status})`);
}

/** Returns false if the user cancelled the untrusted confirm. */
export async function confirmLocalTrust(
  kind: 'mcp' | 'workflow',
  itemId: string,
  label: string,
): Promise<boolean> {
  const trust = await fetchLocalTrust().catch(() => ({
    untrusted_confirm: true,
    trusted_mcp_ids: [] as string[],
    trusted_workflow_ids: [] as string[],
  }));
  const known = kind === 'mcp' ? trust.trusted_mcp_ids : trust.trusted_workflow_ids;
  if (!trust.untrusted_confirm || known.includes(itemId)) return true;
  const ok = window.confirm(
    kind === 'mcp'
      ? `Trust MCP server “${label}” and enable it?`
      : `Trust workflow “${label}” and use it in Chat?`,
  );
  if (!ok) return false;
  await rememberTrustedId(kind, itemId);
  return true;
}

export async function clearCrossSessionMemory(): Promise<number> {
  const response = await sidecarFetch(`${BASE}/api/preferences/cross-session-memory/clear`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`cross-session-memory clear failed (${response.status})`);
  const body = (await response.json()) as { cleared: number };
  return body.cleared ?? 0;
}
