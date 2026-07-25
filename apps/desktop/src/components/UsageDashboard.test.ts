import { describe, expect, it } from 'vitest';
import { usageRowsFromSessions } from './UsageDashboard';
import type { SessionRecord } from '../services/runApi';

function row(id: string, started: string, title?: string): SessionRecord {
  return {
    run_id: id,
    workflow_id: '',
    status: 'idle',
    started_at: started,
    title,
  };
}

describe('usageRowsFromSessions', () => {
  it('sorts by started_at desc and pins current run', () => {
    const sessions = [
      row('run_old', '2026-01-01T10:00:00Z', 'Old'),
      row('run_new', '2026-02-01T10:00:00Z', 'New'),
      row('run_mid', '2026-01-15T10:00:00Z', 'Mid'),
    ];
    const rows = usageRowsFromSessions(sessions, 'run_old');
    expect(rows[0].run_id).toBe('run_old');
    expect(rows[1].run_id).toBe('run_new');
  });

  it('dedupes duplicate run ids', () => {
    const sessions = [row('run_a', '2026-01-01T10:00:00Z'), row('run_a', '2026-01-02T10:00:00Z')];
    expect(usageRowsFromSessions(sessions)).toHaveLength(1);
  });
});
