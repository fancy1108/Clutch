import { beforeEach, describe, expect, it, vi } from 'vitest';

const storage = new Map<string, string>();

beforeEach(() => {
  storage.clear();
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => {
      storage.set(key, value);
    },
    removeItem: (key: string) => {
      storage.delete(key);
    },
  });
});

describe('workspaceViewMode', () => {
  it('defaults to chat when storage empty', async () => {
    vi.resetModules();
    const { loadWorkspaceViewMode } = await import('./workspaceViewMode');
    expect(loadWorkspaceViewMode()).toBe('chat');
  });

  it('persists terminal mode', async () => {
    vi.resetModules();
    const { loadWorkspaceViewMode, saveWorkspaceViewMode } = await import('./workspaceViewMode');
    saveWorkspaceViewMode('terminal');
    expect(loadWorkspaceViewMode()).toBe('terminal');
    saveWorkspaceViewMode('chat');
  });

  it('allows terminal for all CLI agent types', async () => {
    vi.resetModules();
    const { isTerminalCapableAgentType, resolveCliToolForTerminal } = await import('./workspaceViewMode');
    expect(isTerminalCapableAgentType('claude-cli')).toBe(true);
    expect(isTerminalCapableAgentType('opencode-cli')).toBe(true);
    expect(isTerminalCapableAgentType('codex-cli')).toBe(true);
    expect(isTerminalCapableAgentType('aider-cli')).toBe(true);
    expect(isTerminalCapableAgentType('codebuddy-cli')).toBe(true);
    expect(isTerminalCapableAgentType('rivet-cli')).toBe(true);
    expect(isTerminalCapableAgentType('ollama-cli')).toBe(true);
    expect(isTerminalCapableAgentType('antigravity-cli')).toBe(true);
    expect(isTerminalCapableAgentType('custom-tool-cli')).toBe(true);
    expect(isTerminalCapableAgentType('clutch')).toBe(false);
    expect(resolveCliToolForTerminal('codex-cli')).toBe('codex-cli');
    expect(resolveCliToolForTerminal('clutch')).toBeNull();
  });

  it('maps engine hints for display fallback only', async () => {
    vi.resetModules();
    const { resolveCliToolFromEngineHint } = await import('./workspaceViewMode');
    expect(resolveCliToolFromEngineHint('OpenCode CLI')).toBe('opencode-cli');
    expect(resolveCliToolFromEngineHint('Claude CLI')).toBe('claude-cli');
    expect(resolveCliToolFromEngineHint('Codex CLI')).toBe('codex-cli');
    expect(resolveCliToolFromEngineHint('MiMo-V2.5 Free')).toBeNull();
  });

  it('filters footer agents to CLI types only in terminal mode', async () => {
    vi.resetModules();
    const { filterAgentsForTerminalWorkspace } = await import('./workspaceViewMode');
    const agents = [
      { id: '1', agentType: 'claude-cli' },
      { id: '2', agentType: 'codex-cli' },
      { id: '3', agentType: 'clutch' },
    ];
    const resolve = (agent: { agentType?: string }) => agent.agentType ?? '';
    expect(filterAgentsForTerminalWorkspace(agents, 'chat', resolve)).toHaveLength(3);
    expect(filterAgentsForTerminalWorkspace(agents, 'terminal', resolve)).toEqual([
      { id: '1', agentType: 'claude-cli' },
      { id: '2', agentType: 'codex-cli' },
    ]);
  });
});
