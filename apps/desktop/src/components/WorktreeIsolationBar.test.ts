import { describe, expect, it } from 'vitest';
import {
  canAddParallelWorktree,
  spawnErrorFromBody,
  worktreeBarVisible,
} from './WorktreeIsolationBar';

const enabled = {
  id: 'wt_1',
  path: '/tmp/wt_1',
  branch: 'clutch/wt_1',
  enabled: true,
};

describe('WorktreeIsolationBar', () => {
  it('hides idle Add parallel on empty Chat', () => {
    expect(worktreeBarVisible(null, [], null)).toBe(false);
    expect(canAddParallelWorktree(null)).toBe(false);
    expect(canAddParallelWorktree({ ...enabled, enabled: false })).toBe(false);
  });

  it('shows spawn only after isolation is enabled', () => {
    expect(worktreeBarVisible(enabled, [], null)).toBe(true);
    expect(canAddParallelWorktree(enabled)).toBe(true);
  });

  it('surfaces FastAPI string detail instead of spawn failed', () => {
    expect(
      spawnErrorFromBody(
        { detail: 'Workspace is not a git repository; worktree isolation requires git.' },
        'spawn failed',
      ),
    ).toBe('Workspace is not a git repository; worktree isolation requires git.');
  });
});
