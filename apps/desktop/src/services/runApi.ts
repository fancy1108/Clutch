import { sidecarHttpUrl, sidecarFetch } from './sidecarUrl';

export type SessionMode = 'coding' | 'design';

export interface SessionRecord {
  run_id: string;
  workspace_id?: string;
  workspace_name?: string;
  title?: string;
  workflow_id: string;
  mode?: SessionMode;
  status: string;
  started_at: string;
  ended_at?: string;
  /** Design mode: SVG/data-URL preview of generated UI (or reference image). */
  thumbnail_url?: string | null;
  /** Design mode: live HTML preview path when real UI exists (sidebar iframe). */
  ui_preview_url?: string | null;
  /** Design mode: `web` | `app` from session manifest. */
  device?: string | null;
}

/** @deprecated use SessionRecord */
export type RunHistoryRecord = SessionRecord;

/**
 * Desktop sidebar lists every project and buckets rows by `workspace_id`.
 * Scoping history to the active workspace empties other folders until click-switch.
 * Pass `allWorkspaces: true` for any setSessions / refreshSessions path.
 */
export function resolveSessionHistoryWorkspaceId(options: {
  activeWorkspaceId?: string | null;
  allWorkspaces?: boolean;
}): string | undefined {
  if (options.allWorkspaces) return undefined;
  return options.activeWorkspaceId ?? undefined;
}

export async function fetchSessions(
  workspaceId?: string,
  mode?: SessionMode,
): Promise<SessionRecord[]> {
  const params = new URLSearchParams();
  if (workspaceId) params.set('workspace_id', workspaceId);
  if (mode) params.set('mode', mode);
  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await sidecarFetch(sidecarHttpUrl(`/api/runs/history${query}`));
  if (!response.ok) {
    throw new Error(`Failed to load sessions (${response.status})`);
  }
  const body = (await response.json()) as { runs: SessionRecord[] };
  return body.runs;
}

/** @deprecated use fetchSessions */
export const fetchRunHistory = fetchSessions;

export async function createSession(input: {
  run_id: string;
  title?: string;
  workflow_id?: string;
  mode?: SessionMode;
  status?: string;
}): Promise<SessionRecord> {
  const payload: Record<string, string> = {
    run_id: input.run_id,
    mode: input.mode ?? 'coding',
  };
  if (input.title != null) payload.title = input.title;
  if (input.workflow_id != null) payload.workflow_id = input.workflow_id;
  // Only send status when caller sets it — avoids title updates resurrecting "running".
  if (input.status != null) payload.status = input.status;
  const response = await sidecarFetch(sidecarHttpUrl('/api/sessions'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = (body as { detail?: { message?: string } }).detail?.message || 'Failed to create session';
    throw new Error(message);
  }
  return response.json() as Promise<SessionRecord>;
}

export async function startWorkflowRun(
  runId: string,
  workflowId: string,
  instruction: string,
): Promise<{ run_id: string; status: string; state: import('../types').ClutchState }> {
  const response = await sidecarFetch(sidecarHttpUrl(`/api/runs/${runId}/start`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workflow_id: workflowId, instruction }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = (body as { detail?: { message?: string } }).detail?.message || `Failed to start workflow (${response.status})`;
    throw new Error(message);
  }
  return response.json() as Promise<{ run_id: string; status: string; state: import('../types').ClutchState }>;
}

export async function fetchRunState(
  runId: string,
): Promise<{ run_id: string; state: import('../types').ClutchState }> {
  const response = await sidecarFetch(sidecarHttpUrl(`/api/runs/${encodeURIComponent(runId)}/state`));
  if (!response.ok) {
    throw new Error(`Failed to load session state (${response.status})`);
  }
  return response.json() as Promise<{ run_id: string; state: import('../types').ClutchState }>;
}

export async function deleteSession(runId: string): Promise<void> {
  const response = await sidecarFetch(sidecarHttpUrl(`/api/runs/${encodeURIComponent(runId)}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete session (${response.status})`);
  }
}

export interface CompactResult {
  run_id: string;
  compacted: boolean;
  message_count: number;
  session_tokens?: number;
  detail?: string;
}

/** D18 — force context compaction for the active run. */
export async function compactRun(runId: string): Promise<CompactResult> {
  const response = await sidecarFetch(
    sidecarHttpUrl(`/api/runs/${encodeURIComponent(runId)}/compact`),
    { method: 'POST' },
  );
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: { message?: string } | string;
    };
    const msg =
      typeof body.detail === 'string'
        ? body.detail
        : body.detail?.message ?? `compact failed (${response.status})`;
    throw new Error(msg);
  }
  return (await response.json()) as CompactResult;
}
