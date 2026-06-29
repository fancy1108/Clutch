import { sidecarHttpUrl, sidecarFetch } from './sidecarUrl';

export interface ShellSnapshotSummary {
  run_id: string;
  workspace_path: string;
  cwd: string;
  task_summary: string;
  open_todos: string[];
  cli_session_id?: string | null;
  captured_at: string;
}

export async function fetchShellSnapshots(): Promise<ShellSnapshotSummary[]> {
  const response = await sidecarFetch(sidecarHttpUrl('/api/shell-snapshots'));
  if (!response.ok) {
    throw new Error(`Failed to load shell snapshots (${response.status})`);
  }
  const body = (await response.json()) as { snapshots: ShellSnapshotSummary[] };
  return body.snapshots ?? [];
}
