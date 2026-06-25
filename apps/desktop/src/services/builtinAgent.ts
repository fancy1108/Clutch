import type { Agent } from '../types';

export const BUILTIN_AGENT_ID = 'clutch-agent';

export function getBuiltinAgent(): Agent {
  return {
    id: BUILTIN_AGENT_ID,
    name: 'Clutch Agent',
    description: 'System built-in general-purpose agent for supervised workspace tasks.',
    markdownDoc: [
      '# Clutch Agent',
      '',
      'You are Clutch Agent, the default system agent for single-agent sessions.',
      '',
      '## Protocol',
      '- Understand the user\'s goal in the active workspace.',
      '- Propose clear, incremental steps before making changes.',
      '- Ask for approval when execution is risky or ambiguous.',
    ].join('\n'),
    lastModified: 'Built-in',
    avatar: '',
    deliverables: [],
    mcpTools: [],
    mcpServerIds: [],
    aiEngine: 'Configured LLM',
    skills: [],
    builtin: true,
  };
}

export function mergeAgentsWithBuiltin(agents: Agent[]): Agent[] {
  const savedBuiltin = agents.find(
    (agent) => agent.id === BUILTIN_AGENT_ID || agent.builtin,
  );
  const userAgents = agents.filter(
    (agent) => agent.id !== BUILTIN_AGENT_ID && !agent.builtin,
  );
  const builtin = savedBuiltin
    ? { ...getBuiltinAgent(), ...savedBuiltin, id: BUILTIN_AGENT_ID, builtin: true }
    : getBuiltinAgent();
  return [builtin, ...userAgents];
}

export function isBuiltinAgent(agent: Pick<Agent, 'id' | 'builtin'> | null | undefined): boolean {
  return Boolean(agent?.builtin || agent?.id === BUILTIN_AGENT_ID);
}

export function getAgentDisplayName(agent: Agent | undefined): string {
  if (!agent) return '—';
  return agent.name;
}
