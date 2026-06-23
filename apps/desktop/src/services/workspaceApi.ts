export interface WorkspaceInfo {
  id: string;
  workspace_path: string;
  name: string;
}

export interface WorkspacesList {
  workspaces: WorkspaceInfo[];
  active_id: string | null;
}

export interface FileTreeNode {
  name: string;
  path: string;
  type: 'folder' | 'file';
  children?: FileTreeNode[];
}

const BASE = 'http://localhost:8123';

function stableWorkspaceId(path: string): string {
  return `ws_${btoa(path).replace(/[^a-zA-Z0-9]/g, '').slice(0, 12)}`;
}

function parseApiError(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object' || !('detail' in body)) return fallback;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === 'string') {
    return detail === 'Not Found' ? fallback : detail;
  }
  if (detail && typeof detail === 'object' && 'message' in detail) {
    return String((detail as { message: unknown }).message);
  }
  return fallback;
}

function normalizeWorkspace(body: Record<string, unknown>): WorkspaceInfo {
  const workspace_path = String(body.workspace_path ?? '');
  const name = String(body.name ?? workspace_path.split('/').pop() ?? 'workspace');
  const id = typeof body.id === 'string' ? body.id : stableWorkspaceId(workspace_path);
  return { id, workspace_path, name };
}

async function sidecarFetch(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(
      `Cannot reach Clutch Sidecar at ${BASE} (${detail}). Quit other Clutch windows or dev servers using port 8123, then reopen the app.`,
    );
  }
}

export async function fetchWorkspaces(): Promise<WorkspacesList> {
  const response = await sidecarFetch(`${BASE}/api/workspaces`);
  if (response.status === 404) {
    const active = await fetchWorkspace();
    if (!active) return { workspaces: [], active_id: null };
    return { workspaces: [active], active_id: active.id };
  }
  if (!response.ok) throw new Error(`workspaces list failed (${response.status})`);
  return response.json() as Promise<WorkspacesList>;
}

export async function fetchWorkspace(): Promise<WorkspaceInfo | null> {
  const response = await sidecarFetch(`${BASE}/api/workspace`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`workspace fetch failed (${response.status})`);
  const body = (await response.json()) as Record<string, unknown>;
  return normalizeWorkspace(body);
}

export async function addWorkspace(path: string): Promise<WorkspaceInfo> {
  let response = await sidecarFetch(`${BASE}/api/workspaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (response.status === 404) {
    response = await sidecarFetch(`${BASE}/api/workspace`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiError(body, 'Workspace authorize failed'));
  }
  const body = (await response.json()) as Record<string, unknown>;
  return normalizeWorkspace(body);
}

/** @deprecated use addWorkspace */
export const authorizeWorkspace = addWorkspace;

export async function activateWorkspace(workspaceId: string): Promise<WorkspaceInfo> {
  const response = await sidecarFetch(`${BASE}/api/workspaces/${encodeURIComponent(workspaceId)}/activate`, {
    method: 'POST',
  });
  if (response.status === 404) {
    const active = await fetchWorkspace();
    if (active?.id === workspaceId) return active;
    throw new Error('Workspace switch is not supported by this Sidecar version');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(parseApiError(body, 'Workspace switch failed'));
  }
  const body = (await response.json()) as Record<string, unknown>;
  return normalizeWorkspace(body);
}

export async function removeWorkspace(workspaceId: string): Promise<void> {
  const response = await sidecarFetch(`${BASE}/api/workspaces/${encodeURIComponent(workspaceId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`remove workspace failed (${response.status})`);
}

export async function fetchWorkspaceTree(): Promise<FileTreeNode[]> {
  const response = await sidecarFetch(`${BASE}/api/workspace/tree`);
  if (!response.ok) throw new Error(`workspace tree failed (${response.status})`);
  const body = (await response.json()) as { nodes: FileTreeNode[] };
  return body.nodes;
}

export async function fetchWorkspaceFile(path: string): Promise<string> {
  const response = await sidecarFetch(`${BASE}/api/workspace/file?path=${encodeURIComponent(path)}`);
  if (!response.ok) throw new Error(`read file failed (${response.status})`);
  const body = (await response.json()) as { content: string };
  return body.content;
}

export async function reassignToBuilder(runId: string, instructions = 'reassign_to_builder'): Promise<void> {
  const response = await sidecarFetch(`${BASE}/api/runs/${runId}/reassign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ instructions }),
  });
  if (!response.ok) throw new Error(`reassign failed (${response.status})`);
}
