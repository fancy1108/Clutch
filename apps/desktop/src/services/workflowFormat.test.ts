import { describe, expect, it } from 'vitest';
import {
  formatCanvasIncompatibilities,
  getCanvasIncompatibilities,
  isCanvasCompatible,
  canvasToCompiler,
  compilerToCanvas,
  validWhenValues,
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

  it('accepts human_gate with conditional edges as canvas compatible', () => {
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
    expect(isCanvasCompatible(workflow)).toBe(true);
    expect(reasons).toEqual([]);
  });

  it('accepts check nodes with passed/failed edges as canvas compatible', () => {
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
    expect(isCanvasCompatible(workflow)).toBe(true);
    expect(reasons).toEqual([]);
  });

  it('rejects conditional edges on agent_task nodes (not gate/check)', () => {
    const workflow = {
      nodes: [
        { id: 'n1', type: 'agent_task' },
        { id: 'end', type: 'end' },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'n1' },
        { id: 'e2', source: 'n1', target: 'end', data: { when: 'passed' } },
      ],
    };
    const reasons = getCanvasIncompatibilities(workflow);
    expect(isCanvasCompatible(workflow)).toBe(false);
    expect(reasons.some((r) => r.kind === 'conditional_edge_on_linear')).toBe(true);
  });

  it('rejects excessive branching (>3) on human_gate', () => {
    const workflow = {
      nodes: [
        { id: 'gate', type: 'human_gate' },
        { id: 'a', type: 'agent_task' },
        { id: 'b', type: 'agent_task' },
        { id: 'c', type: 'agent_task' },
        { id: 'd', type: 'agent_task' },
        { id: 'end', type: 'end' },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'gate' },
        { id: 'e2', source: 'gate', target: 'a', data: { when: 'approve' } },
        { id: 'e3', source: 'gate', target: 'b', data: { when: 'reject' } },
        { id: 'e4', source: 'gate', target: 'c', data: { when: 'retry' } },
        { id: 'e5', source: 'gate', target: 'd', data: { when: 'approve' } }, // 4th — exceeds 3
        { id: 'e6', source: 'a', target: 'end' },
        { id: 'e7', source: 'b', target: 'end' },
        { id: 'e8', source: 'c', target: 'end' },
        { id: 'e9', source: 'd', target: 'end' },
      ],
    };
    const reasons = getCanvasIncompatibilities(workflow);
    expect(reasons.some((r) => r.kind === 'excessive_branching')).toBe(true);
  });

  it('rejects unsupported node types', () => {
    const workflow = {
      nodes: [
        { id: 'n1', type: 'agent_task' },
        { id: 'unknown', type: 'not_a_type' },
        { id: 'end', type: 'end' },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'n1' },
        { id: 'e2', source: 'n1', target: 'unknown' },
        { id: 'e3', source: 'unknown', target: 'end' },
      ],
    };
    const reasons = getCanvasIncompatibilities(workflow);
    expect(reasons.some((r) => r.kind === 'unsupported_node_type')).toBe(true);
  });

  it('compilerToCanvas preserves human_gate node type', () => {
    const workflow = {
      id: 'test',
      name: 'Test',
      version: 1,
      nodes: [
        { id: 'write', type: 'agent_task', data: { label: 'Write', agent: 'a1', instruction: 'Write something' } },
        { id: 'review', type: 'human_gate', data: { label: 'Review' } },
        { id: 'end', type: 'end', data: { label: 'Finish' } },
      ],
      edges: [
        { id: 'e1', source: 'start', target: 'write' },
        { id: 'e2', source: 'write', target: 'review' },
        { id: 'e3', source: 'review', target: 'end', data: { when: 'approve' } },
        { id: 'e4', source: 'review', target: 'write', data: { when: 'reject' } },
      ],
    };
    const canvas = compilerToCanvas(workflow);
    expect(canvas.steps).toHaveLength(2);
    const gateStep = canvas.steps.find((s) => s.id === 'review');
    expect(gateStep).toBeDefined();
    expect(gateStep!.nodeType).toBe('human_gate');
    expect(gateStep!.edgeWhen).toBeDefined();
    expect(gateStep!.edgeWhen!['end']).toEqual(['approve']);
    expect(gateStep!.edgeWhen!['write']).toEqual(['reject']);
  });

  it('canvasToCompiler produces human_gate nodes with conditional edges', () => {
    const canvas = {
      id: 'test',
      name: 'Test',
      lastDeployed: '—',
      isActive: false,
      icon: 'fork_right',
      steps: [
        { id: 'write', name: 'Write', nodeType: 'agent_task' as const, agent: 'a1', description: 'Write things', nextSteps: ['review'] },
        { id: 'review', name: 'Review Content', nodeType: 'human_gate' as const, agent: '', description: '', nextSteps: ['end', 'write'], edgeWhen: { end: ['approve'], write: ['reject'] } },
      ],
      description: '',
    };
    const compiler = canvasToCompiler(canvas);
    const gateNode = compiler.nodes.find((n) => n.id === 'review');
    expect(gateNode).toBeDefined();
    expect(gateNode!.type).toBe('human_gate');
    const approveEdge = compiler.edges.find((e) => e.source === 'review' && e.target === 'end');
    expect(approveEdge).toBeDefined();
    expect(approveEdge!.data?.when).toBe('approve');
    const rejectEdge = compiler.edges.find((e) => e.source === 'review' && e.target === 'write');
    expect(rejectEdge).toBeDefined();
    expect(rejectEdge!.data?.when).toBe('reject');
  });

  it('validWhenValues returns correct values for each node type', () => {
    expect(validWhenValues('human_gate')).toEqual(['approve', 'reject', 'retry']);
    expect(validWhenValues('check')).toEqual(['passed', 'failed']);
    expect(validWhenValues('agent_task')).toEqual([]);
    expect(validWhenValues(undefined)).toEqual([]);
  });
});