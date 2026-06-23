export interface WorkspaceInfo {
  workspace_path: string;
  name: string;
}

export interface FileTreeNode {
  name: string;
  path: string;
  type: 'folder' | 'file';
  children?: FileTreeNode[];
}

const BASE = 'http://localhost:8123';

export async function fetchWorkspace(): Promise<WorkspaceInfo | null> {
  const response = await fetch(`${BASE}/api/workspace`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`workspace fetch failed (${response.status})`);
  return response.json() as Promise<WorkspaceInfo>;
}

export async function authorizeWorkspace(path: string): Promise<WorkspaceInfo> {
  const response = await fetch(`${BASE}/api/workspace`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error((body as { detail?: { message?: string } }).detail?.message || '授权失败');
  }
  return response.json() as Promise<WorkspaceInfo>;
}

export async function fetchWorkspaceTree(): Promise<FileTreeNode[]> {
  const response = await fetch(`${BASE}/api/workspace/tree`);
  if (!response.ok) throw new Error(`workspace tree failed (${response.status})`);
  const body = (await response.json()) as { nodes: FileTreeNode[] };
  return body.nodes;
}

export async function fetchWorkspaceFile(path: string): Promise<string> {
  const response = await fetch(`${BASE}/api/workspace/file?path=${encodeURIComponent(path)}`);
  if (!response.ok) throw new Error(`read file failed (${response.status})`);
  const body = (await response.json()) as { content: string };
  return body.content;
}

export async function reassignToBuilder(runId: string, instructions = 'reassign_to_builder'): Promise<void> {
  const response = await fetch(`${BASE}/api/runs/${runId}/reassign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ instructions }),
  });
  if (!response.ok) throw new Error(`reassign failed (${response.status})`);
}
