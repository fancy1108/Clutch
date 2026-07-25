import { describe, expect, it } from 'vitest';
import {
  findDispatchEntryIdForStep,
  findLogIndexForStep,
  isTerminalSyncableStep,
  resolveChatTerminalSyncTarget,
  resolveSyncLaneId,
  stepSearchNeedle,
} from './chatTerminalSync';
import type { ToolStep } from '../types';

const shellStep = (overrides: Partial<ToolStep> = {}): ToolStep => ({
  id: 's1',
  kind: 'execute',
  tool: 'clutch-tools__run_terminal_cmd',
  status: 'completed',
  title: 'Run echo hi',
  detail: '{"command":"echo hi"}',
  ...overrides,
});

describe('chatTerminalSync', () => {
  it('allows any tool trail step to sync into Terminal audit', () => {
    expect(isTerminalSyncableStep(shellStep())).toBe(true);
    expect(
      isTerminalSyncableStep({
        id: 'r',
        kind: 'fetch',
        tool: 'web_fetch',
        status: 'completed',
        title: 'Fetched example.com',
        detail: 'https://example.com/a',
      }),
    ).toBe(true);
  });

  it('extracts command needle from JSON detail', () => {
    expect(stepSearchNeedle(shellStep())).toBe('echo hi');
  });

  it('resolves focused lane then primary', () => {
    expect(
      resolveSyncLaneId({
        focused_lane_id: 'lane_builder',
        pty_lanes: [{ lane_id: 'lane_primary', focused: true }],
      }),
    ).toBe('lane_builder');
    expect(resolveSyncLaneId({ pty_lanes: [] })).toBe('lane_primary');
  });

  it('finds latest matching chat step log line', () => {
    const logs = [
      '[CHAT] Step 1: clutch-tools__run_terminal_cmd args={"command":"echo hi"}',
      '[CHAT] Tool response length: 3 chars',
      '[CHAT] Step 2: clutch-tools__run_terminal_cmd args={"command":"echo hi"}',
    ];
    expect(findLogIndexForStep(logs, shellStep())).toBe(2);
  });

  it('matches dispatch history by prompt', () => {
    const id = findDispatchEntryIdForStep(
      [
        {
          id: 'd1',
          time: '',
          sources_label: '',
          target: 'claude',
          prompt: 'please echo hi',
          handoff_file: '',
          handoff_path: '',
        },
        {
          id: 'd2',
          time: '',
          sources_label: '',
          target: 'claude',
          prompt: 'other',
          handoff_file: '',
          handoff_path: '',
        },
      ],
      shellStep(),
    );
    expect(id).toBe('d1');
  });

  it('builds a sync target bundle', () => {
    const target = resolveChatTerminalSyncTarget(shellStep(), {
      focused_lane_id: null,
      pty_lanes: [{ lane_id: 'lane_primary', status: 'running' }],
      terminal_logs: [
        '[CHAT] Step 1: clutch-tools__run_terminal_cmd args={"command":"echo hi"}',
      ],
      dispatch_log: [],
    });
    expect(target.laneId).toBe('lane_primary');
    expect(target.logIndex).toBe(0);
  });
});
