import { describe, expect, it } from 'vitest';
import {
  formatCanvasIncompatibilities,
  getCanvasIncompatibilities,
  isCanvasCompatible,
} from '../services/workflowFormat';

describe('workflowFormat', () => {
  it('marks linear workflows as canvas compatible', () => {
    const workflow = {
      nodes: [
        { id: 'n1', type: 'agent_task' },
        { id: 'end', type: 'end' },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'n1' },
        { id: 'e2', source: 'n1', target: 'end' },
      ],
    };
    expect(isCanvasCompatible(workflow)).toBe(true);
    expect(getCanvasIncompatibilities(workflow)).toEqual([]);
  });

  it('marks empty start-to-end workflows as canvas compatible', () => {
    const workflow = {
      nodes: [{ id: 'end', type: 'end' }],
      edges: [{ id: 'e1', source: 'start', target: 'end' }],
    };
    expect(isCanvasCompatible(workflow)).toBe(true);
  });

  it('lists human_gate and conditional edges as canvas incompatibilities (#55)', () => {
    const workflow = {
      nodes: [
        { id: 'builder', type: 'agent_task' },
        { id: 'review-gate', type: 'human_gate' },
        { id: 'end', type: 'end' },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'builder' },
        { id: 'e2', source: 'builder', target: 'review-gate' },
        { id: 'e4', source: 'review-gate', target: 'end', data: { when: 'approve' } },
        { id: 'e5', source: 'review-gate', target: 'builder', data: { when: 'reject' } },
      ],
    };
    const reasons = getCanvasIncompatibilities(workflow);
    expect(isCanvasCompatible(workflow)).toBe(false);
    expect(reasons).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          kind: 'unsupported_node_type',
          nodeId: 'review-gate',
          nodeType: 'human_gate',
        }),
        expect.objectContaining({
          kind: 'conditional_edge',
          edgeId: 'e5',
          when: 'reject',
        }),
        expect.objectContaining({
          kind: 'branching_node',
          nodeId: 'review-gate',
        }),
      ]),
    );
    const summary = formatCanvasIncompatibilities(reasons);
    expect(summary).toContain('review-gate');
    expect(summary).toContain('human_gate');
    expect(summary).toContain('e5');
  });

  it('lists check nodes as unsupported for canvas', () => {
    const workflow = {
      nodes: [
        { id: 'n1', type: 'agent_task' },
        { id: 'verify', type: 'check' },
        { id: 'end', type: 'end' },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'n1' },
        { id: 'e2', source: 'n1', target: 'verify' },
        { id: 'e3', source: 'verify', target: 'end', data: { when: 'passed' } },
      ],
    };
    const reasons = getCanvasIncompatibilities(workflow);
    expect(reasons.some((r) => r.kind === 'unsupported_node_type' && r.nodeId === 'verify')).toBe(
      true,
    );
  });
});
