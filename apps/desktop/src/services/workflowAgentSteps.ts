/** Resolve ordered workflow agent steps and in-progress step for chat Thinking UI. */

import type { Agent, ChatMessage } from '../types';
import { agentTypeFromAgent, agentTypeLabel, type AgentTypeId } from './agentTypes';
import { getAgentDisplayName } from './builtinAgent';
import type { CompilerWorkflow } from './workflowFormat';

export interface WorkflowAgentStep {
  nodeId: string;
  label: string;
  agentRef: string;
  agentName: string;
  agentType: string;
  toolId: string;
}

const WORKFLOW_SYSTEM_AGENTS = new Set(['Builder', 'Orchestrator', 'Evaluator', 'Supervisor']);

const TOOL_LABELS: Record<string, string> = {
  clutch: 'Clutch',
  llm: 'Clutch',
  'claude-cli': 'Claude CLI',
  'ollama-cli': 'Ollama CLI',
  'antigravity-cli': 'Antigravity CLI',
  'codex-cli': 'Codex CLI',
  'agy-cli': 'Antigravity CLI',
  agy: 'Antigravity CLI',
};

export function workflowToolLabel(tool?: string): string {
  const key = (tool ?? '').trim().toLowerCase();
  if (!key) return 'Clutch';
  return TOOL_LABELS[key] ?? tool.trim();
}

export function isWorkflowSystemAgent(name: string | undefined): boolean {
  if (!name?.trim()) return false;
  return WORKFLOW_SYSTEM_AGENTS.has(name.trim());
}

/** Flow refine: pause mid-run, or tweak after passed/failed. */
export function isWorkflowRefineEligible(
  status: string | undefined,
  workflowId: string | null | undefined,
): boolean {
  if (!workflowId?.trim()) return false;
  return status === 'refining' || status === 'passed' || status === 'failed';
}

export function isWorkflowRefineMessage(text: string, status: string | undefined): boolean {
  if (status === 'refining') return true;
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (/^\/(continue|resume)\b/i.test(trimmed)) return true;
  if (trimmed === '继续' || trimmed === '继续执行' || trimmed === '继续工作流') return true;
  return /^@\S/.test(trimmed);
}

export function shouldRouteWorkflowRefine(
  status: string | undefined,
  workflowId: string | null | undefined,
  text: string,
): boolean {
  if (!isWorkflowRefineEligible(status, workflowId)) return false;
  return isWorkflowRefineMessage(text, status);
}

export function parseWorkflowMention(
  text: string,
  steps: WorkflowAgentStep[],
): { mention: string | null; body: string } {
  const trimmed = text.trim();
  if (!trimmed.startsWith('@')) {
    return { mention: null, body: trimmed };
  }
  const rest = trimmed.slice(1).trimStart();
  const candidates = new Map<string, WorkflowAgentStep>();
  for (const step of steps) {
    if (step.label.trim()) candidates.set(step.label.trim(), step);
    if (step.agentName.trim()) candidates.set(step.agentName.trim(), step);
  }
  const sorted = [...candidates.keys()].sort((a, b) => b.length - a.length);
  for (const name of sorted) {
    if (rest === name || rest.startsWith(`${name} `)) {
      return { mention: name, body: rest.slice(name.length).trim() };
    }
  }
  const fallback = rest.match(/^(\S+)\s*(.*)$/s);
  if (!fallback) return { mention: null, body: trimmed };
  return { mention: fallback[1], body: fallback[2].trim() };
}

/** Resolve @mention in flow refine mode to a configured agent id. */
export function resolveWorkflowMentionAgentId(
  text: string,
  steps: WorkflowAgentStep[],
  agents: Agent[],
): string | null {
  const { mention } = parseWorkflowMention(text, steps);
  if (!mention) return null;
  const token = mention.trim();
  const lower = token.toLowerCase();
  for (const step of steps) {
    if (
      step.agentName === token
      || step.label === token
      || step.agentName.toLowerCase() === lower
      || step.label.toLowerCase() === lower
    ) {
      const rec = resolveAgentRecord(step.agentRef, agents);
      if (rec?.id) return rec.id;
    }
  }
  const direct = agents.find(
    (agent) =>
      agent.id === token
      || agent.name === token
      || getAgentDisplayName(agent) === token
      || agent.name.toLowerCase() === lower
      || getAgentDisplayName(agent).toLowerCase() === lower,
  );
  return direct?.id ?? null;
}

export function resolveAgentDisplayName(agentRef: string, agents: Agent[]): string {
  const matched = resolveAgentRecord(agentRef, agents);
  if (matched) return getAgentDisplayName(matched);
  return agentRef.trim();
}

/** Match workflow node agent ref to a configured Agent (fuzzy). */
export function resolveAgentRecord(agentRef: string, agents: Agent[]): Agent | undefined {
  const ref = agentRef.trim();
  if (!ref) return undefined;
  const lower = ref.toLowerCase();
  const exact = agents.find(
    (agent) =>
      agent.id === ref
      || agent.name === ref
      || getAgentDisplayName(agent) === ref,
  );
  if (exact) return exact;
  return agents.find((agent) => {
    const name = agent.name.toLowerCase();
    const display = getAgentDisplayName(agent).toLowerCase();
    return (
      name === lower
      || display === lower
      || name.includes(lower)
      || lower.includes(name)
      || display.includes(lower)
      || lower.includes(display)
    );
  });
}

function nodeToolToAgentTypeId(tool?: string): AgentTypeId {
  const key = (tool ?? '').trim().toLowerCase();
  if (key === 'claude-cli') return 'claude-cli';
  if (key === 'ollama-cli' || key === 'ollama') return 'ollama-cli';
  if (key === 'antigravity-cli' || key === 'agy-cli' || key === 'agy') return 'antigravity-cli';
  if (key === 'codex-cli' || key === 'codex') return 'codex-cli';
  if (key === 'aider-cli' || key === 'aider') return 'aider-cli';
  return 'clutch';
}

function resolveStepAgentType(agentRef: string, tool: string | undefined, agents: Agent[]): {
  agentType: string;
  toolId: string;
} {
  const matched = resolveAgentRecord(agentRef, agents);
  const typeId = matched ? agentTypeFromAgent(matched) : nodeToolToAgentTypeId(tool);
  return {
    agentType: agentTypeLabel(typeId),
    toolId: typeId,
  };
}

export function findWorkflowStep(
  steps: WorkflowAgentStep[],
  params: { activeNodeId?: string; activeAgentName?: string },
): WorkflowAgentStep | undefined {
  const { activeNodeId, activeAgentName } = params;
  if (activeNodeId) {
    const byNode = steps.find((step) => step.nodeId === activeNodeId);
    if (byNode) return byNode;
  }
  const ref = (activeAgentName ?? '').trim().toLowerCase();
  if (!ref) return undefined;
  return steps.find(
    (step) =>
      step.agentName.toLowerCase() === ref
      || step.agentRef.toLowerCase() === ref
      || step.label.toLowerCase() === ref,
  ) ?? steps.find(
    (step) =>
      step.agentName.toLowerCase().includes(ref)
      || ref.includes(step.agentName.toLowerCase())
      || step.agentRef.toLowerCase().includes(ref)
      || ref.includes(step.agentRef.toLowerCase()),
  );
}

export function orderedWorkflowAgentSteps(
  workflow: CompilerWorkflow,
  agents: Agent[],
): WorkflowAgentStep[] {
  const agentNodes = workflow.nodes.filter((node) => node.type === 'agent_task');
  if (agentNodes.length === 0) return [];

  const nodeById = new Map(agentNodes.map((node) => [node.id, node]));
  const edgesBySource = new Map<string, string[]>();
  for (const edge of workflow.edges) {
    const targets = edgesBySource.get(edge.source) ?? [];
    targets.push(edge.target);
    edgesBySource.set(edge.source, targets);
  }

  const ordered: WorkflowAgentStep[] = [];
  const visited = new Set<string>();
  const queue = ['start'];

  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const target of edgesBySource.get(current) ?? []) {
      if (visited.has(target) || target === 'end') continue;
      visited.add(target);
      const node = nodeById.get(target);
      if (node) {
        const data = node.data as { label?: string; agent?: string; tool?: string };
        const agentRef = String(data.agent ?? '').trim();
        const label = String(data.label ?? node.id);
        const tool = String(data.tool ?? 'clutch').trim().toLowerCase() || 'clutch';
        const { agentType, toolId } = resolveStepAgentType(agentRef || label, tool, agents);
        ordered.push({
          nodeId: node.id,
          label,
          agentRef,
          agentName: resolveAgentDisplayName(agentRef || label, agents),
          agentType,
          toolId,
        });
      }
      queue.push(target);
    }
  }

  if (ordered.length > 0) return ordered;

  return agentNodes.map((node) => {
    const data = node.data as { label?: string; agent?: string; tool?: string };
    const agentRef = String(data.agent ?? '').trim();
    const label = String(data.label ?? node.id);
    const tool = String(data.tool ?? 'clutch').trim().toLowerCase() || 'clutch';
    const { agentType, toolId } = resolveStepAgentType(agentRef || label, tool, agents);
    return {
      nodeId: node.id,
      label,
      agentRef,
      agentName: resolveAgentDisplayName(agentRef || label, agents),
      agentType,
      toolId,
    };
  });
}

/** First in-progress workflow step — prefers backend active node, then reply count. */
export function resolveInProgressWorkflowStep(
  steps: WorkflowAgentStep[],
  messages: ChatMessage[],
  options?: { activeNodeId?: string; activeAgentName?: string },
): WorkflowAgentStep | null {
  if (steps.length === 0) return null;

  const fromActive = findWorkflowStep(steps, {
    activeNodeId: options?.activeNodeId,
    activeAgentName: options?.activeAgentName,
  });
  if (fromActive) return fromActive;

  const lastUserIndex = messages.findLastIndex((message) => message.agent === 'User');
  const afterUser = messages.slice(lastUserIndex + 1);
  const agentReplyCount = afterUser.filter(
    (message) => message.agent !== 'User' && message.agent !== 'System',
  ).length;
  if (agentReplyCount >= steps.length) return null;
  return steps[agentReplyCount] ?? null;
}

/** Map workflow agent reply index (after latest user message) for agent-type labels. */
export function buildWorkflowReplyStepIndex(
  steps: WorkflowAgentStep[],
  messages: ChatMessage[],
): Map<string, number> {
  const map = new Map<string, number>();
  if (steps.length === 0) return map;
  const lastUserIndex = messages.findLastIndex((message) => message.agent === 'User');
  let replyIndex = 0;
  for (const message of messages.slice(lastUserIndex + 1)) {
    if (message.agent === 'User' || message.agent === 'System') continue;
    map.set(message.id, replyIndex);
    replyIndex += 1;
  }
  return map;
}
