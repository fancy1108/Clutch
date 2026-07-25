import { describe, expect, it } from 'vitest';
import { resolveSessionBoardStatus, sessionBoardRows } from './SessionOverviewBoard';
import type { SessionRecord } from '../services/runApi';

const base = (overrides: Partial<SessionRecord>): SessionRecord => ({
  run_id: 'run_a',
  workflow_id: '',
  status: 'idle',
  started_at: '2026-07-25T10:00:00Z',
  ...overrides,
});

describe('SessionOverviewBoard', () => {
  it('marks active running session', () => {
    const session = base({ run_id: 'run_live', status: 'running' });
    expect(resolveSessionBoardStatus(session, 'run_live', 'running')).toBe('running');
    expect(resolveSessionBoardStatus(session, 'run_other', 'idle')).toBe('running');
  });

  it('marks completed sessions as done', () => {
    const session = base({ status: 'passed' });
    expect(resolveSessionBoardStatus(session, 'run_other', 'idle')).toBe('done');
  });

  it('dedupes and sorts session rows', () => {
    const rows = sessionBoardRows([
      base({ run_id: 'run_old', started_at: '2026-07-24T10:00:00Z' }),
      base({ run_id: 'run_new', started_at: '2026-07-25T12:00:00Z' }),
      base({ run_id: 'run_new', started_at: '2026-07-25T12:00:00Z' }),
    ]);
    expect(rows.map((row) => row.run_id)).toEqual(['run_new', 'run_old']);
  });
});
