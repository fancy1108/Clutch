import type { BackgroundJob } from '../types';

/** D26 — detect a background job that just left the running state with failure. */
export function detectBgJobFailureToast(
  prev: BackgroundJob[],
  current: BackgroundJob[],
): string | null {
  for (const job of current) {
    if (job.status !== 'failed' && job.status !== 'killed') continue;
    const before = prev.find((item) => item.id === job.id);
    if (before?.status !== 'running') continue;
    return job.title || job.command || job.id;
  }
  return null;
}
