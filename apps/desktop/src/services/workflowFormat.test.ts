import { describe, expect, it } from 'vitest';
import { isCanvasCompatible } from '../services/workflowFormat';

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
  });

  it('marks empty start-to-end workflows as canvas compatible', () => {
    const workflow = {
      nodes: [{ id: 'end', type: 'end' }],
      edges: [{ id: 'e1', source: 'start', target: 'end' }],
    };
    expect(isCanvasCompatible(workflow)).toBe(true);
  });
});
