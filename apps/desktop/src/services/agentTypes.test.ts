import { describe, expect, it } from 'vitest';

import {
  CLUTCH_AGENT_TYPE,
  agentTypeOptionsFromTools,
  buildSelectableAgentTypeOptions,
} from './agentTypes';
import type { AiToolStatus } from './toolsApi';

function tool(partial: Partial<AiToolStatus> & Pick<AiToolStatus, 'id' | 'name'>): AiToolStatus {
  return {
    description: '',
    icon: 'terminal',
    kind: 'cli',
    path: '/usr/local/bin/x',
    installed: true,
    connected: false,
    registered: false,
    ...partial,
  };
}

describe('agentTypes', () => {
  it('always includes Clutch and connected CLI tools', () => {
    const options = agentTypeOptionsFromTools([
      tool({ id: 'codex-cli', name: 'OpenAI Codex CLI', connected: true, registered: true, agentType: 'codex-cli' }),
      tool({ id: 'claude-cli', name: 'Claude Code CLI', connected: true, registered: false, agentType: 'claude-cli' }),
      tool({ id: 'agy-cli', name: 'Antigravity CLI', connected: false, registered: true, agentType: 'antigravity-cli' }),
    ]);
    expect(options).toEqual([
      { id: CLUTCH_AGENT_TYPE, label: 'Clutch' },
      { id: 'codex-cli', label: 'Codex CLI' },
      { id: 'claude-cli', label: 'Claude CLI (needs Auto-configure)' },
    ]);
  });

  it('includes Ollama when connected even if agentType is missing from API', () => {
    const options = agentTypeOptionsFromTools([
      tool({ id: 'ollama-cli', name: 'Ollama', connected: true, registered: true, agentType: null }),
    ]);
    expect(options.some((item) => item.id === 'ollama-cli' && item.label === 'Ollama')).toBe(true);
  });

  it('buildSelectableAgentTypeOptions keeps current selection when tools list is empty', () => {
    const options = buildSelectableAgentTypeOptions([], 'codex-cli');
    expect(options.some((item) => item.id === 'codex-cli')).toBe(true);
  });
});
