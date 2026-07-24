import { describe, expect, it } from 'vitest';
import { resolveSessionHistoryWorkspaceId } from './runApi';

describe('resolveSessionHistoryWorkspaceId', () => {
  it('omits workspace_id for sidebar so every project can show its history', () => {
    expect(
      resolveSessionHistoryWorkspaceId({
        activeWorkspaceId: 'ws-ecc',
        allWorkspaces: true,
      }),
    ).toBeUndefined();
  });

  it('keeps workspace filter when explicitly scoped', () => {
    expect(
      resolveSessionHistoryWorkspaceId({
        activeWorkspaceId: 'ws-test',
        allWorkspaces: false,
      }),
    ).toBe('ws-test');
  });
});
