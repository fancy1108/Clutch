import { describe, expect, it } from 'vitest';
import {
  filterSessionBoardRows,
  getSessionBoardActionLabel,
  resolveSessionBoardStatus,
  sessionBoardRows,
  summarizeSessionBoardStatus,
} from './SessionOverviewBoard';
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

  it('marks approval-waiting sessions as waiting', () => {
    const session = base({ status: 'waiting_approval' });
    expect(resolveSessionBoardStatus(session, 'run_other', 'idle')).toBe('waiting');
  });

  it('marks failed sessions as failed', () => {
    const session = base({ status: 'failed' });
    expect(resolveSessionBoardStatus(session, 'run_other', 'idle')).toBe('failed');
  });

  it('uses action labels for review and follow-up states', () => {
    expect(getSessionBoardActionLabel('waiting', 'en')).toBe('Review');
    expect(getSessionBoardActionLabel('failed', 'zh')).toBe('检查');
    expect(getSessionBoardActionLabel('running', 'en')).toBe('Follow');
  });

  it('summarizes task-center counts by status', () => {
    const sessions = [
      base({ run_id: 'run_running', status: 'running' }),
      base({ run_id: 'run_waiting', status: 'waiting_approval' }),
      base({ run_id: 'run_failed', status: 'failed' }),
      base({ run_id: 'run_done', status: 'completed' }),
      base({ run_id: 'run_idle', status: 'queued' }),
    ];

    expect(summarizeSessionBoardStatus(sessions)).toEqual({
      running: 1,
      done: 1,
      waiting: 1,
      failed: 1,
      idle: 1,
    });
  });

  it('filters sessions by board status', () => {
    const sessions = [
      base({ run_id: 'run_running', status: 'running' }),
      base({ run_id: 'run_waiting', status: 'waiting_approval' }),
      base({ run_id: 'run_failed', status: 'failed' }),
      base({ run_id: 'run_done', status: 'completed' }),
    ];

    expect(filterSessionBoardRows(sessions, 'all').map((session) => session.run_id)).toEqual([
      'run_running',
      'run_waiting',
      'run_failed',
      'run_done',
    ]);
    expect(filterSessionBoardRows(sessions, 'waiting').map((session) => session.run_id)).toEqual(['run_waiting']);
    expect(filterSessionBoardRows(sessions, 'failed').map((session) => session.run_id)).toEqual(['run_failed']);
  });

  it('dedupes and sorts session rows', () => {
    const rows = sessionBoardRows([
      base({ run_id: 'run_old', started_at: '2026-07-24T10:00:00Z' }),
      base({ run_id: 'run_new', started_at: '2026-07-25T12:00:00Z' }),
      base({ run_id: 'run_new', started_at: '2026-07-25T12:00:00Z' }),
    ]);
    expect(rows.map((row) => row.run_id)).toEqual(['run_new', 'run_old']);
  });

  it('sorts by updated_at when an older session is touched', () => {
    const rows = sessionBoardRows([
      base({
        run_id: 'run_old',
        started_at: '2026-07-20T10:00:00Z',
        updated_at: '2026-07-25T18:00:00Z',
      }),
      base({
        run_id: 'run_mid',
        started_at: '2026-07-24T12:00:00Z',
        updated_at: '2026-07-24T12:00:00Z',
      }),
    ]);
    expect(rows.map((row) => row.run_id)).toEqual(['run_old', 'run_mid']);
  });
});
