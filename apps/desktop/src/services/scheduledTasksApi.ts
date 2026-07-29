import { sidecarFetch } from './sidecarUrl';

const BASE = '';

export interface ScheduledTask {
  id: string;
  title: string;
  prompt: string;
  interval_sec: number;
  enabled: boolean;
  run_agent_turn: boolean;
  agent_id?: string;
  workspace_path?: string;
}

export async function listScheduledTasks(): Promise<ScheduledTask[]> {
  const res = await sidecarFetch(`${BASE}/api/scheduled-tasks`);
  if (!res.ok) return [];
  const data = (await res.json()) as { tasks?: ScheduledTask[] };
  return data.tasks ?? [];
}

export async function createScheduledTask(body: {
  title?: string;
  prompt: string;
  interval_sec: number;
  enabled?: boolean;
  run_agent_turn?: boolean;
  confirm?: boolean;
}): Promise<ScheduledTask | null> {
  const res = await sidecarFetch(`${BASE}/api/scheduled-tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { task?: ScheduledTask };
  return data.task ?? null;
}

export async function deleteScheduledTask(taskId: string): Promise<boolean> {
  const res = await sidecarFetch(`${BASE}/api/scheduled-tasks/${encodeURIComponent(taskId)}`, {
    method: 'DELETE',
  });
  return res.ok;
}
