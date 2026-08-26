import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

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
  tools?: Array<{ name: string; description: string; inputSchema?: any }>;
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
  const response = await sidecarFetch(`${BASE}/api/mcp/status`);
  if (!response.ok) throw new Error(`mcp status failed (${response.status})`);
  return response.json() as Promise<McpStatusResponse>;
}

export async function registerMcpServer(payload: {
  name: string;
  transport: 'stdio' | 'sse';
  endpoint: string;
  env?: Record<string, string>;
}): Promise<McpStatusResponse> {
  const response = await sidecarFetch(`${BASE}/api/mcp/servers/register`, {
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
  const response = await sidecarFetch(`${BASE}/api/mcp/servers/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id }),
  });
  if (!response.ok) throw new Error(`mcp remove failed (${response.status})`);
  return response.json() as Promise<McpStatusResponse>;
}

export async function toggleMcpServer(id: string, enabled: boolean): Promise<McpStatusResponse> {
  const response = await sidecarFetch(`${BASE}/api/mcp/servers/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, enabled }),
  });
  if (!response.ok) throw new Error(`mcp toggle failed (${response.status})`);
  return response.json() as Promise<McpStatusResponse>;
}

export async function saveMcpConfig(servers: any[]): Promise<McpStatusResponse> {
  const response = await sidecarFetch(`${BASE}/api/mcp/config/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ servers }),
  });
  if (!response.ok) throw new Error(`mcp config save failed (${response.status})`);
  return response.json() as Promise<McpStatusResponse>;
}

export interface McpProbeResult {
  id: string;
  name: string;
  ok: boolean;
  toolsCount: number;
  tools: Array<{ name: string; description?: string }>;
  error: string | null;
}

/** D38 — per-server Test connection. */
export async function testMcpServer(id: string): Promise<McpProbeResult> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 135_000);
  try {
    const response = await sidecarFetch(`${BASE}/api/mcp/servers/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
      throw new Error(body.detail?.message ?? `mcp test failed (${response.status})`);
    }
    return response.json() as Promise<McpProbeResult>;
  } finally {
    window.clearTimeout(timer);
  }
}

export async function fetchMcpOAuthLoginUrl(): Promise<string | null> {
  const response = await sidecarFetch(`${BASE}/api/mcp/oauth-login-url`);
  if (!response.ok) return null;
  const body = (await response.json()) as { url?: string | null };
  return body.url || null;
}

export interface McpResourceItem {
  uri: string;
  name: string;
  description?: string | null;
  mimeType?: string | null;
}

export interface McpResourcePin {
  server_id: string;
  uri: string;
  name: string;
  mimeType?: string | null;
  text?: string | null;
}

/** D43 — list resources for a Hub server. */
export async function listMcpResources(serverId: string): Promise<{
  server_id: string;
  name: string;
  resources: McpResourceItem[];
  count: number;
}> {
  const response = await sidecarFetch(
    `${BASE}/api/mcp/servers/${encodeURIComponent(serverId)}/resources`,
  );
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `mcp resources failed (${response.status})`);
  }
  return response.json();
}

export async function readMcpResource(
  serverId: string,
  uri: string,
): Promise<{ text: string; uri: string }> {
  const response = await sidecarFetch(`${BASE}/api/mcp/servers/resources/read`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: serverId, uri }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `mcp resource read failed (${response.status})`);
  }
  return response.json();
}

export async function fetchMcpResourcePins(): Promise<McpResourcePin[]> {
  const response = await sidecarFetch(`${BASE}/api/mcp/resource-pins`);
  if (!response.ok) return [];
  const body = (await response.json()) as { pins?: McpResourcePin[] };
  return body.pins ?? [];
}

export async function pinMcpResource(pin: {
  server_id: string;
  uri: string;
  name?: string;
  mimeType?: string | null;
}): Promise<McpResourcePin[]> {
  const response = await sidecarFetch(`${BASE}/api/mcp/resource-pins`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(pin),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `pin failed (${response.status})`);
  }
  const body = (await response.json()) as { pins?: McpResourcePin[] };
  return body.pins ?? [];
}

export async function unpinMcpResource(serverId: string, uri: string): Promise<McpResourcePin[]> {
  const response = await sidecarFetch(`${BASE}/api/mcp/resource-pins/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ server_id: serverId, uri }),
  });
  if (!response.ok) throw new Error(`unpin failed (${response.status})`);
  const body = (await response.json()) as { pins?: McpResourcePin[] };
  return body.pins ?? [];
}

