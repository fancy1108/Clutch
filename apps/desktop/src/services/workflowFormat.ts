/**
 * Canvas ↔ compiler JSON mapping.
 *
 * Supported on the visual canvas: agent_task, human_gate, check, end.
 * human_gate/check nodes may have up to 3 outgoing edges with `when` values
 * (approve/reject/retry for gates; passed/failed for checks).
 */

import type { WorkflowDef, WorkflowStep, EdgeWhen } from '../types';

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

/** Node types renderable on the canvas (everything except virtual start). */
const CANVAS_NODE_TYPES = new Set(['agent_task', 'human_gate', 'check', 'end']);

/** Valid `when` values for edges leaving human_gate nodes. */
const GATE_WHEN_VALUES = new Set<EdgeWhen>(['approve', 'reject', 'retry']);
/** Valid `when` values for edges leaving check nodes. */
const CHECK_WHEN_VALUES = new Set<EdgeWhen>(['passed', 'failed']);
/** Maximum outgoing edges from a branching node (gate/check). */
const MAX_BRANCH_OUT = 3;

export type CanvasIncompatibility =
  | { kind: 'multiple_end_nodes'; count: number }
  | { kind: 'unsupported_node_type'; nodeId: string; nodeType: string }
  | { kind: 'conditional_edge'; edgeId: string; source: string; target: string; when: string }
  | { kind: 'conditional_edge_on_linear'; edgeId: string; source: string; target: string; when: string }
  | { kind: 'invalid_start'; outDegree: number }
  | { kind: 'invalid_end'; nodeId: string; inDegree: number }
  | { kind: 'branching_node'; nodeId: string; outDegree: number }
  | { kind: 'excessive_branching'; nodeId: string; outDegree: number; nodeType: string }
  | { kind: 'merge_or_cycle'; nodeId: string; inDegree: number }
  | { kind: 'isolated_node'; nodeId: string };

function slugId(name: string): string {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  return base || `step-${Date.now()}`;
}

/** Collect every reason the canvas editor cannot host this workflow. */
export function getCanvasIncompatibilities(
  workflow: Pick<CompilerWorkflow, 'nodes' | 'edges'>,
): CanvasIncompatibility[] {
  const reasons: CanvasIncompatibility[] = [];
  const endNodes = workflow.nodes.filter((n) => n.type === 'end');
  if (endNodes.length !== 1) {
    reasons.push({ kind: 'multiple_end_nodes', count: endNodes.length });
  }

  const nodeMap = new Map(workflow.nodes.map((n) => [n.id, n]));

  for (const node of workflow.nodes) {
    if (!CANVAS_NODE_TYPES.has(node.type)) {
      reasons.push({
        kind: 'unsupported_node_type',
        nodeId: node.id,
        nodeType: node.type,
      });
    }
  }

  const outCount: Record<string, number> = {};
  const inCount: Record<string, number> = {};
  for (const edge of workflow.edges) {
    outCount[edge.source] = (outCount[edge.source] ?? 0) + 1;
    inCount[edge.target] = (inCount[edge.target] ?? 0) + 1;
  }

  const startOut = outCount.start ?? 0;
  if (startOut !== 1) {
    reasons.push({ kind: 'invalid_start', outDegree: startOut });
  }

  // Validate conditional edges
  for (const edge of workflow.edges) {
    if (!edge.data?.when) continue;
    const sourceNode = nodeMap.get(edge.source);
    if (!sourceNode) continue;
    const whenValues: EdgeWhen[] = Array.isArray(edge.data.when) ? edge.data.when : [edge.data.when];
    const isValid = whenValues.every((w) => {
      if (sourceNode.type === 'human_gate') return GATE_WHEN_VALUES.has(w as EdgeWhen);
      if (sourceNode.type === 'check') return CHECK_WHEN_VALUES.has(w as EdgeWhen);
      return false;
    });
    if (isValid) continue;
    // Conditional edge on a linear node (agent_task) — invalid
    reasons.push({
      kind: 'conditional_edge_on_linear',
      edgeId: edge.id,
      source: edge.source,
      target: edge.target,
      when: String(edge.data.when),
    });
  }

  const agentNodes = workflow.nodes.filter((n) => n.type === 'agent_task');
  if (agentNodes.length === 0 && endNodes.length === 1) {
    const endId = endNodes[0].id;
    const endIn = inCount[endId] ?? 0;
    const hasStartToEnd = workflow.edges.some((e) => e.source === 'start' && e.target === endId);
    if (!(endIn === 1 && hasStartToEnd)) {
      reasons.push({ kind: 'invalid_end', nodeId: endId, inDegree: endIn });
    }
    return reasons;
  }

  for (const node of workflow.nodes) {
    if (node.type === 'end') {
      const endIn = inCount[node.id] ?? 0;
      if (endIn !== 1) {
        reasons.push({ kind: 'invalid_end', nodeId: node.id, inDegree: endIn });
      }
      continue;
    }
    if (node.type === 'start') continue;
    const out = outCount[node.id] ?? 0;
    const inc = inCount[node.id] ?? 0;
    const isGate = node.type === 'human_gate' || node.type === 'check';
    if (isGate) {
      if (out > MAX_BRANCH_OUT) {
        reasons.push({ kind: 'excessive_branching', nodeId: node.id, outDegree: out, nodeType: node.type });
      }
    } else {
      if (out > 1) {
        reasons.push({ kind: 'branching_node', nodeId: node.id, outDegree: out });
      }
    }
    // Allow merges when the extra incoming edge is from a human_gate/check (loopback)
    if (inc > 1) {
      const incomingEdges = workflow.edges.filter((e) => e.target === node.id);
      const nonGateIncoming = incomingEdges.filter((e) => {
        const src = nodeMap.get(e.source);
        return src && src.type !== 'human_gate' && src.type !== 'check';
      });
      if (nonGateIncoming.length > 1) {
        reasons.push({ kind: 'merge_or_cycle', nodeId: node.id, inDegree: inc });
      }
    }
    if (out === 0 && inc === 0) {
      reasons.push({ kind: 'isolated_node', nodeId: node.id });
    }
  }

  return reasons;
}

/** Human-readable summary for the JSON-mode banner (#55). */
export function formatCanvasIncompatibilities(reasons: CanvasIncompatibility[]): string {
  return reasons
    .map((r) => {
      switch (r.kind) {
        case 'multiple_end_nodes':
          return `end nodes: ${r.count} (need 1)`;
        case 'unsupported_node_type':
          return `node ${r.nodeId} (${r.nodeType})`;
        case 'conditional_edge':
        case 'conditional_edge_on_linear':
          return `edge ${r.edgeId} ${r.source}→${r.target} (when:${r.when})`;
        case 'invalid_start':
          return `start out-degree ${r.outDegree} (need 1)`;
        case 'invalid_end':
          return `end ${r.nodeId} in-degree ${r.inDegree} (need 1)`;
        case 'branching_node':
          return `node ${r.nodeId} branches (out:${r.outDegree})`;
        case 'excessive_branching':
          return `node ${r.nodeId} (${r.nodeType}) has ${r.outDegree} outgoing (max ${MAX_BRANCH_OUT})`;
        case 'merge_or_cycle':
          return `node ${r.nodeId} merge/cycle (in:${r.inDegree})`;
        case 'isolated_node':
          return `node ${r.nodeId} isolated`;
        default:
          return 'unknown';
      }
    })
    .join('; ');
}

/** True when workflow can be hosted on the visual canvas. */
export function isCanvasCompatible(workflow: Pick<CompilerWorkflow, 'nodes' | 'edges'>): boolean {
  return getCanvasIncompatibilities(workflow).length === 0;
}

/** Valid `when` values for a given node type. */
export function validWhenValues(nodeType: string | undefined): EdgeWhen[] {
  if (nodeType === 'human_gate') return ['approve', 'reject', 'retry'];
  if (nodeType === 'check') return ['passed', 'failed'];
  return [];
}

export function compilerToCanvas(workflow: CompilerWorkflow, icon = 'account_tree'): WorkflowDef {
  const canvasNodes = workflow.nodes.filter((n) => CANVAS_NODE_TYPES.has(n.type) && n.type !== 'end');

  const nodeTypeMap = new Map(workflow.nodes.map((n) => [n.id, n.type]));

  const steps: WorkflowStep[] = canvasNodes.map((node) => {
    const data = node.data as {
      label?: string;
      agent?: string;
      tool?: string;
      instruction?: string;
      prompt?: string;
    };
    const incoming = workflow.edges.filter((e) => e.target === node.id);
    const outgoing = workflow.edges.filter((e) => e.source === node.id);

    // Collect edge `when` values for conditional routing
    const edgeWhen: Record<string, EdgeWhen[]> = {};
    for (const e of outgoing) {
      if (e.data?.when) {
        const raw = e.data.when;
        edgeWhen[e.target] = Array.isArray(raw) ? raw : [raw];
      }
    }

    const nodeType = (node.type === 'human_gate' || node.type === 'check') ? node.type : 'agent_task';

    return {
      id: node.id,
      name: data.label ?? node.id,
      nodeType,
      agent: data.agent ?? '',
      aiTool: data.tool,
      description: data.instruction ?? data.prompt ?? '',
      nextSteps: outgoing.map((e) => e.target).filter((t) => t !== 'end'),
      edgeWhen: Object.keys(edgeWhen).length > 0 ? edgeWhen : undefined,
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
  const compilerNodes: CompilerNode[] = canvas.steps.map((step, idx) => {
    const nodeType = step.nodeType ?? 'agent_task';
    const position = step.position ?? { x: 250, y: idx * 120 + 80 };

    if (nodeType === 'human_gate' || nodeType === 'check') {
      const data: Record<string, unknown> = {
        label: step.name || (nodeType === 'human_gate' ? 'Human Approval' : 'Check'),
      };
      if (nodeType === 'check' && step.description) {
        data.prompt = step.description;
      }
      return {
        id: String(step.id),
        type: nodeType,
        position,
        data,
      };
    }

    return {
      id: String(step.id),
      type: 'agent_task',
      position,
      data: {
        label: step.name,
        agent: step.agent,
        ...(step.aiTool ? { tool: step.aiTool } : {}),
        instruction: step.description || step.name,
      },
    };
  });

  const endNode: CompilerNode = {
    id: 'end',
    type: 'end',
    position: { x: 250, y: canvas.steps.length * 120 + 80 },
    data: { label: 'Finish' },
  };

  const edges: CompilerEdge[] = [];
  let edgeIdx = 1;

  if (canvas.steps.length === 0) {
    edges.push({ id: `e${edgeIdx++}`, source: 'start', target: 'end' });
  } else {
    edges.push({ id: `e${edgeIdx++}`, source: 'start', target: String(canvas.steps[0].id) });
  }

  // Build a set of all node ids for quick lookup
  const stepIds = new Set(canvas.steps.map((s) => String(s.id)));
  const nodeTypeById = new Map(canvas.steps.map((s) => [String(s.id), s.nodeType ?? 'agent_task']));

  for (const step of canvas.steps) {
    const targets = step.nextSteps?.length
      ? step.nextSteps
      : [];
    const nodeType = step.nodeType ?? 'agent_task';
    const edgeWhen = (step as any).edgeWhen as Record<string, EdgeWhen[]> | undefined;

    for (const target of targets) {
      const targetId = target === 'end' ? 'end' : String(target);
      const edge: CompilerEdge = {
        id: `e${edgeIdx++}`,
        source: String(step.id),
        target: targetId,
      };
      // Add conditional when for gate/check nodes
      const whenVals = edgeWhen?.[targetId] ?? edgeWhen?.[target];
      if (whenVals && whenVals.length > 0) {
        edge.data = { when: whenVals.length === 1 ? whenVals[0] : whenVals };
      }
      edges.push(edge);
    }
  }

  // Ensure end is reachable: if no edges point to end yet, connect the last agent_task
  // or the last branching node without explicit nextSteps to end.
  if (!edges.some((e) => e.target === 'end') && canvas.steps.length > 0) {
    // Find nodes that have no outgoing edges
    const sourcesWithEdges = new Set(edges.map((e) => e.source));
    const terminalSteps = canvas.steps.filter((s) => !sourcesWithEdges.has(String(s.id)));
    for (const step of terminalSteps) {
      edges.push({
        id: `e${edgeIdx++}`,
        source: String(step.id),
        target: 'end',
      });
    }
  }

  const rawId = canvas.id || slugId(canvas.name);
  const id = rawId.match(/^[a-z0-9]+(?:-[a-z0-9]+)*$/) ? rawId : slugId(canvas.name);

  return {
    id,
    name: canvas.name,
    version: base?.version ?? 1,
    nodes: [...compilerNodes, endNode],
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
