const BASE = 'http://localhost:8123';

export interface McpServer {
  id: string;
  name: string;
  type: 'local' | 'remote';
  transport: 'stdio' | 'sse' | 'websocket';
  endpoint: string;
  status: 'connected' | 'reconnecting' | 'failed';
  toolsCount: number;
  lastHeartbeat: string;
  builtin?: boolean;
  enabled?: boolean;
}

export interface McpStatusResponse {
  filesystem: {
    connected: boolean;
    tools: number;
    workspace_path?: string | null;
  };
  servers: McpServer[];
}

export async function fetchMcpStatus(): Promise<McpStatusResponse> {
  const response = await fetch(`${BASE}/api/mcp/status`);
  if (!response.ok) throw new Error(`mcp status failed (${response.status})`);
  return response.json() as Promise<McpStatusResponse>;
}

export async function registerMcpServer(payload: {
  name: string;
  transport: 'stdio' | 'sse';
  endpoint: string;
}): Promise<McpStatusResponse> {
  const response = await fetch(`${BASE}/api/mcp/servers/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `mcp register failed (${response.status})`);
  }
  return response.json() as Promise<McpStatusResponse>;
}

export async function removeMcpServer(id: string): Promise<McpStatusResponse> {
  const response = await fetch(`${BASE}/api/mcp/servers/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id }),
  });
  if (!response.ok) throw new Error(`mcp remove failed (${response.status})`);
  return response.json() as Promise<McpStatusResponse>;
}

export async function toggleMcpServer(id: string, enabled: boolean): Promise<McpStatusResponse> {
  const response = await fetch(`${BASE}/api/mcp/servers/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, enabled }),
  });
  if (!response.ok) throw new Error(`mcp toggle failed (${response.status})`);
  return response.json() as Promise<McpStatusResponse>;
}
