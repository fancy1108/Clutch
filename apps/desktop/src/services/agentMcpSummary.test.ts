import { describe, expect, it } from 'vitest';
import { buildMcpBindingSummary } from './agentMcpSummary';

describe('buildMcpBindingSummary', () => {
  it('marks unbound when no ids', () => {
    expect(buildMcpBindingSummary([], [{ id: 'local-fs', name: 'FS', toolsCount: 10 }])).toEqual({
      serverCount: 0,
      approxTools: 0,
      names: [],
      unbound: true,
    });
  });

  it('counts bound servers and tools', () => {
    const summary = buildMcpBindingSummary(
      ['local-fs', 'mcp_abc'],
      [
        { id: 'local-fs', name: 'Local FS', toolsCount: 12 },
        { id: 'mcp_abc', name: 'Git', toolsCount: 3, enabled: true },
        { id: 'other', name: 'Other', toolsCount: 99 },
      ],
    );
    expect(summary.unbound).toBe(false);
    expect(summary.serverCount).toBe(2);
    expect(summary.approxTools).toBe(15);
    expect(summary.names).toEqual(['Local FS', 'Git']);
  });
});
