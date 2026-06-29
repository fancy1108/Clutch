import { describe, expect, it, vi, beforeEach } from 'vitest';

import type { Agent } from '../types';
import {
  buildAgentFromConnectedTool,
  ensureAgentForConnectedTool,
  findExistingAgentForTool,
} from './agentProvisioning';
import type { AiToolStatus } from './toolsApi';

vi.mock('./agentApi', () => ({
  fetchAgents: vi.fn(),
  saveAgents: vi.fn(),
}));

vi.mock('./sidecarUrl', () => ({
  sidecarFetch: vi.fn(),
  sidecarHttpUrl: (path: string) => path,
}));

import { fetchAgents, saveAgents } from './agentApi';
import { sidecarFetch } from './sidecarUrl';

function tool(partial: Partial<AiToolStatus> & Pick<AiToolStatus, 'id' | 'name'>): AiToolStatus {
  return {
    description: '',
    icon: 'terminal',
    kind: 'cli',
    path: '/usr/local/bin/x',
    installed: true,
    connected: true,
    registered: true,
    ...partial,
  };
}

describe('agentProvisioning', () => {
  beforeEach(() => {
    vi.mocked(fetchAgents).mockReset();
    vi.mocked(saveAgents).mockReset();
    vi.mocked(sidecarFetch).mockReset();
  });

  it('dedupes by agentType (case-insensitive name)', () => {
    const existing: Agent[] = [
      {
        id: 'agent-1',
        name: 'Claude Code CLI',
        description: '',
        markdownDoc: '',
        lastModified: '',
        avatar: '',
        deliverables: [],
        agentType: 'claude-cli',
      },
    ];
    const matched = findExistingAgentForTool(
      tool({ id: 'claude-cli', name: 'claude code cli', agentType: 'claude-cli' }),
      existing,
    );
    expect(matched?.id).toBe('agent-1');
  });

  it('maps agentType from tool id when API omits agentType', () => {
    const created = buildAgentFromConnectedTool(
      tool({ id: 'codex-cli', name: 'OpenAI Codex CLI', agentType: null }),
      'codex-cli',
    );
    expect(created.agentType).toBe('codex-cli');
    expect(created.name).toBe('OpenAI Codex CLI');
  });

  it('does not create Ollama agent when no local models', async () => {
    vi.mocked(sidecarFetch).mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, models: [] }),
    } as Response);
    vi.mocked(fetchAgents).mockResolvedValue([]);

    const result = await ensureAgentForConnectedTool(
      tool({ id: 'ollama-cli', name: 'Ollama', agentType: 'ollama-cli' }),
    );

    expect(result).toBeNull();
    expect(saveAgents).not.toHaveBeenCalled();
  });

  it('creates agent when Ollama models exist', async () => {
    vi.mocked(sidecarFetch).mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, models: ['llama3'] }),
    } as Response);
    vi.mocked(fetchAgents).mockResolvedValue([]);
    vi.mocked(saveAgents).mockResolvedValue();

    const result = await ensureAgentForConnectedTool(
      tool({ id: 'ollama-cli', name: 'Ollama', agentType: 'ollama-cli' }),
    );

    expect(result?.ollamaModel).toBe('llama3');
    expect(saveAgents).toHaveBeenCalledOnce();
  });
});
