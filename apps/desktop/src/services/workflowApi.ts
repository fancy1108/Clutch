/** Sidecar workflow persistence API (M1-09). */

import type { CompilerWorkflow } from './workflowFormat';

import { SIDECAR_BASE as BASE } from './sidecarUrl';

export type WorkflowListItem = {
  id: string;
  name: string;
  source: 'template' | 'user';
  readOnly: boolean;
};

type ApiError = { detail?: { message?: string; errors?: string[] } };

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiError;
    const msg = body.detail?.message ?? 'Request failed';
    const errs = body.detail?.errors?.join(', ') ?? '';
    return errs ? `${msg}: ${errs}` : msg;
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function fetchTemplateIds(): Promise<string[]> {
  const res = await fetch(`${BASE}/api/workflows/templates`);
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { workflow_ids: string[] };
  return body.workflow_ids;
}

export async function fetchUserIds(): Promise<string[]> {
  const res = await fetch(`${BASE}/api/workflows/user`);
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { workflow_ids: string[] };
  return body.workflow_ids;
}

export async function loadTemplateWorkflow(id: string): Promise<CompilerWorkflow> {
  const res = await fetch(`${BASE}/api/workflows/templates/${id}`);
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { workflow: CompilerWorkflow };
  return body.workflow;
}

export async function loadUserWorkflow(id: string): Promise<CompilerWorkflow> {
  const res = await fetch(`${BASE}/api/workflows/user/${id}`);
  if (!res.ok) throw new Error(await parseError(res));
  const body = (await res.json()) as { workflow: CompilerWorkflow };
  return body.workflow;
}

export async function loadWorkflowById(id: string): Promise<CompilerWorkflow> {
  try {
    return await loadTemplateWorkflow(id);
  } catch {
    return loadUserWorkflow(id);
  }
}

export async function saveUserWorkflow(workflow: CompilerWorkflow): Promise<void> {
  const res = await fetch(`${BASE}/api/workflows/user`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workflow }),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function validateWorkflow(workflow: CompilerWorkflow): Promise<void> {
  const res = await fetch(`${BASE}/api/workflows/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workflow }),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function deleteUserWorkflow(id: string): Promise<void> {
  const res = await fetch(`${BASE}/api/workflows/user/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function listWorkflowItems(): Promise<WorkflowListItem[]> {
  const users = await fetchUserIds();
  const items: WorkflowListItem[] = [];

  for (const id of users) {
    try {
      const wf = await loadUserWorkflow(id);
      items.push({ id, name: wf.name, source: 'user', readOnly: false });
    } catch {
      items.push({ id, name: id, source: 'user', readOnly: false });
    }
  }

  return items;
}
