/** Canvas ↔ compiler JSON mapping (D9). Simple linear agent_task chains only. */

import type { WorkflowDef, WorkflowStep } from '../types';

export interface CompilerNode {
  id: string;
  type: string;
  position?: { x: number; y: number };
  data: Record<string, unknown>;
}

export interface CompilerEdge {
  id: string;
  source: string;
  target: string;
  data?: { when?: string };
}

export interface CompilerWorkflow {
  id: string;
  name: string;
  version: number;
  nodes: CompilerNode[];
  edges: CompilerEdge[];
  icon?: string;
  description?: string;
}

function slugId(name: string): string {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  return base || `step-${Date.now()}`;
}

/** True when workflow is a simple linear agent_task pipeline (canvas-safe). */
export function isCanvasCompatible(workflow: CompilerWorkflow): boolean {
  const endNodes = workflow.nodes.filter((n) => n.type === 'end');
  if (endNodes.length !== 1) return false;

  for (const node of workflow.nodes) {
    if (node.type !== 'agent_task' && node.type !== 'end') return false;
  }

  for (const edge of workflow.edges) {
    if (edge.data?.when) return false;
  }

  const outCount: Record<string, number> = {};
  const inCount: Record<string, number> = {};
  for (const edge of workflow.edges) {
    outCount[edge.source] = (outCount[edge.source] ?? 0) + 1;
    inCount[edge.target] = (inCount[edge.target] ?? 0) + 1;
  }

  if ((outCount.start ?? 0) !== 1) return false;

  const agentNodes = workflow.nodes.filter((n) => n.type === 'agent_task');
  if (agentNodes.length === 0) {
    const endId = endNodes[0].id;
    return (
      (inCount[endId] ?? 0) === 1 &&
      workflow.edges.some((e) => e.source === 'start' && e.target === endId)
    );
  }

  for (const node of workflow.nodes) {
    if (node.type === 'end') {
      if ((inCount[node.id] ?? 0) !== 1) return false;
      continue;
    }
    const out = outCount[node.id] ?? 0;
    const inc = inCount[node.id] ?? 0;
    if (out > 1 || inc > 1) return false;
    if (out === 0 && inc === 0) return false;
  }

  return true;
}

export function compilerToCanvas(workflow: CompilerWorkflow, icon = 'account_tree'): WorkflowDef {
  const agentNodes = workflow.nodes.filter((n) => n.type === 'agent_task');
  const edgeBySource = new Map(workflow.edges.map((e) => [e.target, e]));

  const steps: WorkflowStep[] = agentNodes.map((node) => {
    const data = node.data as {
      label?: string;
      agent?: string;
      tool?: string;
      instruction?: string;
    };
    const incoming = workflow.edges.filter((e) => e.target === node.id);
    const outgoing = workflow.edges.filter((e) => e.source === node.id);
    return {
      id: node.id,
      name: data.label ?? node.id,
      agent: data.agent ?? '',
      aiTool: data.tool,
      description: data.instruction ?? '',
      nextSteps: outgoing.map((e) => e.target).filter((t) => t !== 'end'),
      position: node.position,
      fromSteps: incoming.map((e) => e.source).filter((s) => s !== 'start'),
    } as WorkflowStep & { fromSteps?: string[] };
  });

  return {
    id: workflow.id,
    name: workflow.name,
    lastDeployed: '—',
    isActive: false,
    icon: workflow.icon ?? icon,
    description: workflow.description ?? '',
    steps,
  };
}

export function canvasToCompiler(
  canvas: WorkflowDef,
  base?: Partial<CompilerWorkflow>,
): CompilerWorkflow {
  const agentNodes: CompilerNode[] = canvas.steps.map((step, idx) => ({
    id: String(step.id),
    type: 'agent_task',
    position: step.position ?? { x: 250, y: idx * 120 + 80 },
    data: {
      label: step.name,
      agent: step.agent,
      ...(step.aiTool ? { tool: step.aiTool } : {}),
      instruction: step.description || step.name,
    },
  }));

  const endNode: CompilerNode = {
    id: 'end',
    type: 'end',
    position: { x: 250, y: canvas.steps.length * 120 + 80 },
    data: { label: 'Finish' },
  };

  const edges: CompilerEdge[] = [];
  let edgeIdx = 1;

  if (canvas.steps.length === 0) {
    edges.push({
      id: `e${edgeIdx++}`,
      source: 'start',
      target: 'end',
    });
  } else {
    edges.push({
      id: `e${edgeIdx++}`,
      source: 'start',
      target: String(canvas.steps[0].id),
    });
  }

  for (const step of canvas.steps) {
    const targets = step.nextSteps?.length
      ? step.nextSteps
      : canvas.steps.findIndex((s) => s.id === step.id) === canvas.steps.length - 1
        ? ['end']
        : [];
    for (const target of targets) {
      edges.push({
        id: `e${edgeIdx++}`,
        source: String(step.id),
        target: target === 'end' ? 'end' : String(target),
      });
    }
  }

  if (!edges.some((e) => e.target === 'end') && canvas.steps.length > 0) {
    const last = canvas.steps[canvas.steps.length - 1];
    edges.push({
      id: `e${edgeIdx++}`,
      source: String(last.id),
      target: 'end',
    });
  }

  const rawId = canvas.id || slugId(canvas.name);
  const id = rawId.match(/^[a-z0-9]+(?:-[a-z0-9]+)*$/) ? rawId : slugId(canvas.name);

  return {
    id,
    name: canvas.name,
    version: base?.version ?? 1,
    nodes: [...agentNodes, endNode],
    edges,
    icon: canvas.icon,
    description: canvas.description,
  };
}

export function parseCompilerJson(text: string): CompilerWorkflow {
  const parsed = JSON.parse(text) as CompilerWorkflow;
  if (!parsed?.id || !parsed?.nodes || !parsed?.edges) {
    throw new Error('JSON must contain id, nodes, and edges fields');
  }
  return parsed;
}

export function formatCompilerJson(workflow: CompilerWorkflow): string {
  return `${JSON.stringify(workflow, null, 2)}\n`;
}
