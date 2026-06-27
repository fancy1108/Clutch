import { describe, expect, it } from 'vitest';

import type { ChatMessage } from '../types';
import {
  buildWorkflowReplyStepIndex,
  orderedWorkflowAgentSteps,
  resolveInProgressWorkflowStep,
  workflowToolLabel,
} from './workflowAgentSteps';
import type { CompilerWorkflow } from './workflowFormat';

const workflow: CompilerWorkflow = {
  id: 'weather-to-vision',
  name: 'Weather-to-Vision',
  version: 1,
  nodes: [
    { id: 'n1', type: 'agent_task', data: { label: 'Research', agent: 'Researcher', tool: 'llm' } },
    { id: 'n2', type: 'agent_task', data: { label: 'Draw', agent: 'agent-b', tool: 'llm' } },
    { id: 'end', type: 'end', data: {} },
  ],
  edges: [
    { id: 'e1', source: 'start', target: 'n1' },
    { id: 'e2', source: 'n1', target: 'n2' },
    { id: 'e3', source: 'n2', target: 'end' },
  ],
};

const agents = [
  { id: 'agent-a', name: 'The Researcher', agentType: 'claude-cli' },
  { id: 'agent-b', name: 'The Artist', agentType: 'clutch', modelId: 'agnes-image' },
] as const;

describe('workflowAgentSteps', () => {
  it('orders agent steps from start and resolves display names', () => {
    const steps = orderedWorkflowAgentSteps(workflow, [...agents]);
    expect(steps.map((step) => step.agentName)).toEqual(['The Researcher', 'The Artist']);
    expect(steps[0].agentType).toBe('Claude CLI');
    expect(steps[0].toolId).toBe('claude-cli');
    expect(steps[1].agentType).toBe('Clutch');
  });

  it('resolves agent type from configured agent when workflow tool is llm', () => {
    const steps = orderedWorkflowAgentSteps(workflow, [...agents]);
    expect(steps[0].toolId).toBe('claude-cli');
    expect(steps[0].agentType).toBe('Claude CLI');
  });

  it('maps workflow tool ids to labels', () => {
    expect(workflowToolLabel('claude-cli')).toBe('Claude CLI');
    expect(workflowToolLabel('clutch')).toBe('Clutch');
  });

  it('prefers active node over reply-count when backend is on a later step', () => {
    const steps = orderedWorkflowAgentSteps(workflow, [...agents]);
    const messages: ChatMessage[] = [
      { id: 'u1', agent: 'User', text: 'hello', timestamp: '1' },
    ];
    const inProgress = resolveInProgressWorkflowStep(steps, messages, {
      activeNodeId: 'n2',
      activeAgentName: 'The Artist',
    });
    expect(inProgress?.agentName).toBe('The Artist');
    expect(inProgress?.toolId).toBe('clutch');
  });

  it('picks first step before any agent reply', () => {
    const steps = orderedWorkflowAgentSteps(workflow, [...agents]);
    const beforeReply: ChatMessage[] = [
      { id: 'u1', agent: 'User', text: 'hello', timestamp: '1' },
    ];
    expect(resolveInProgressWorkflowStep(steps, beforeReply)?.agentName).toBe('The Researcher');
    expect(resolveInProgressWorkflowStep(steps, beforeReply)?.toolId).toBe('claude-cli');
  });

  it('picks in-progress step by reply count, not agent name spelling', () => {
    const steps = orderedWorkflowAgentSteps(workflow, [...agents]);
    const afterFirst: ChatMessage[] = [
      { id: 'u1', agent: 'User', text: 'hello', timestamp: '1' },
      { id: 'a1', agent: 'The Researcher', text: 'weather', timestamp: '2' },
    ];
    expect(resolveInProgressWorkflowStep(steps, afterFirst)?.agentName).toBe('The Artist');
  });

  it('builds per-message workflow step index', () => {
    const steps = orderedWorkflowAgentSteps(workflow, [...agents]);
    const messages: ChatMessage[] = [
      { id: 'u1', agent: 'User', text: 'hello', timestamp: '1' },
      { id: 'a1', agent: 'The Researcher', text: 'weather', timestamp: '2' },
      { id: 'a2', agent: 'The Artist', text: 'image', timestamp: '3' },
    ];
    const index = buildWorkflowReplyStepIndex(steps, messages);
    expect(index.get('a1')).toBe(0);
    expect(index.get('a2')).toBe(1);
  });
});
