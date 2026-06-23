export interface SessionRecord {
  run_id: string;
  workspace_id?: string;
  workspace_name?: string;
  title?: string;
  workflow_id: string;
  status: string;
  started_at: string;
  ended_at?: string;
}

/** @deprecated use SessionRecord */
export type RunHistoryRecord = SessionRecord;

export async function fetchSessions(workspaceId?: string): Promise<SessionRecord[]> {
  const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
  const response = await fetch(`http://localhost:8123/api/runs/history${query}`);
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
}): Promise<SessionRecord> {
  const response = await fetch('http://localhost:8123/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = (body as { detail?: { message?: string } }).detail?.message || 'Failed to create session';
    throw new Error(message);
  }
  return response.json() as Promise<SessionRecord>;
}
