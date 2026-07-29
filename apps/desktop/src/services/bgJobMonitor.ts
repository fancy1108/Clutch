import type { BackgroundJob } from '../types';

/** D26 — toast only on unexpected failure (not user Kill). */
export function detectBgJobFailureToast(
  prev: BackgroundJob[],
  current: BackgroundJob[],
): string | null {
  for (const job of current) {
    if (job.status !== 'failed') continue;
    const before = prev.find((item) => item.id === job.id);
    if (before?.status !== 'running') continue;
    return job.title || job.command || job.id;
  }
  return null;
}
