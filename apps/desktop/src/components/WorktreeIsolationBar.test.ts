import { describe, expect, it } from 'vitest';
import {
  canAddParallelWorktree,
  footerWorktreeLabel,
  spawnErrorFromBody,
} from './WorktreeIsolationBar';

const enabled = {
  id: 'wt_1',
  path: '/tmp/wt_1',
  branch: 'clutch/wt_1',
  enabled: true,
};

describe('FooterWorktreeMenu', () => {
  it('labels the footer like Branch (em dash when idle)', () => {
    expect(footerWorktreeLabel(null)).toBe('—');
    expect(footerWorktreeLabel({ ...enabled, enabled: false })).toBe('—');
    expect(footerWorktreeLabel(enabled)).toBe('clutch/wt_1');
  });

  it('allows parallel trees only while isolation is bound', () => {
    expect(canAddParallelWorktree(null)).toBe(false);
    expect(canAddParallelWorktree({ ...enabled, enabled: false })).toBe(false);
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
