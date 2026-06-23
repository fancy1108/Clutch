export interface RunHistoryRecord {
  run_id: string;
  workflow_id: string;
  status: string;
  started_at: string;
  ended_at?: string;
}

export async function fetchRunHistory(): Promise<RunHistoryRecord[]> {
  const response = await fetch('http://localhost:8123/api/runs/history');
  if (!response.ok) {
    throw new Error(`Failed to load run history (${response.status})`);
  }
  const body = (await response.json()) as { runs: RunHistoryRecord[] };
  return body.runs;
}
