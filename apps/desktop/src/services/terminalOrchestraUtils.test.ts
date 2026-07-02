import { describe, expect, it } from 'vitest';
import {
  agentDisplayName,
  computeLaneLayout,
  expandedLanes,
  collapsedLanes,
} from './terminalOrchestraUtils';
import type { PtyLane } from '../types';

const sampleLane = (overrides: Partial<PtyLane> = {}): PtyLane => ({
  lane_id: 'lane_a',
  agent_type: 'claude-cli',
  label: 'Task',
  status: 'running',
  focused: true,
  collapsed: false,
  run_id: 'run_1',
  ...overrides,
});

describe('terminalOrchestraUtils', () => {
  it('maps agent types to display names', () => {
    expect(agentDisplayName('claude-cli')).toBe('Claude Code');
    expect(agentDisplayName('opencode-cli')).toBe('OpenCode');
  });

  it('computes grid layout from expanded lane count', () => {
    expect(computeLaneLayout(1)).toBe(1);
    expect(computeLaneLayout(2)).toBe(2);
    expect(computeLaneLayout(4)).toBe(3);
  });

  it('splits expanded and collapsed lanes', () => {
    const lanes = [
      sampleLane({ lane_id: 'a' }),
      sampleLane({ lane_id: 'b', collapsed: true }),
      sampleLane({ lane_id: 'c', status: 'queued' }),
    ];
    expect(expandedLanes(lanes).map((l) => l.lane_id)).toEqual(['a']);
    expect(collapsedLanes(lanes).map((l) => l.lane_id)).toEqual(['b', 'c']);
  });
});
