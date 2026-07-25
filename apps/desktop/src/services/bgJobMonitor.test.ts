import { describe, expect, it } from 'vitest';
import type { BackgroundJob } from '../types';
import { detectBgJobFailureToast } from './bgJobMonitor';

const job = (partial: Partial<BackgroundJob> & Pick<BackgroundJob, 'id' | 'status'>): BackgroundJob => ({
  id: partial.id,
  command: partial.command ?? partial.id,
  title: partial.title ?? partial.command ?? partial.id,
  status: partial.status,
  output: partial.output,
  exit_code: partial.exit_code,
});

describe('bgJobMonitor (D26)', () => {
  it('fires when a running job becomes failed', () => {
    const prev = [job({ id: 'bg_1', status: 'running', command: 'false' })];
    const current = [job({ id: 'bg_1', status: 'failed', command: 'false' })];
    expect(detectBgJobFailureToast(prev, current)).toBe('false');
  });

  it('ignores jobs that were already failed', () => {
    const prev = [job({ id: 'bg_1', status: 'failed' })];
    const current = [job({ id: 'bg_1', status: 'failed' })];
    expect(detectBgJobFailureToast(prev, current)).toBeNull();
  });

  it('does not toast when the user kills a running job', () => {
    const prev = [job({ id: 'bg_1', status: 'running', command: 'sleep 20' })];
    const current = [job({ id: 'bg_1', status: 'killed', command: 'sleep 20' })];
    expect(detectBgJobFailureToast(prev, current)).toBeNull();
  });
});
