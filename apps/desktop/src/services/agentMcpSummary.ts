/**
 * D40 — summarize Agent Hub MCP bindings for Chat badge.
 */

export type McpStatusServerLike = {
  id: string;
  name: string;
  toolsCount?: number;
  enabled?: boolean;
  status?: string;
};

export type McpBindingSummary = {
  /** Bound Hub server count (excludes implicit clutch-tools). */
  serverCount: number;
  approxTools: number;
  names: string[];
  unbound: boolean;
};

export function buildMcpBindingSummary(
  mcpServerIds: string[] | undefined,
  servers: McpStatusServerLike[],
): McpBindingSummary {
  const wanted = new Set(
    (mcpServerIds ?? []).map((id) => id.trim()).filter(Boolean),
  );
  if (wanted.size === 0) {
    return { serverCount: 0, approxTools: 0, names: [], unbound: true };
  }
  const matched = servers.filter(
    (server) => wanted.has(server.id) && server.enabled !== false,
  );
  const names = matched.map((server) => server.name || server.id);
  const approxTools = matched.reduce(
    (sum, server) => sum + (typeof server.toolsCount === 'number' ? server.toolsCount : 0),
    0,
  );
  return {
    serverCount: matched.length || wanted.size,
    approxTools,
    names: names.length ? names : [...wanted],
    unbound: false,
  };
}
