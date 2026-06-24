import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchMcpStatus,
  registerMcpServer,
  removeMcpServer,
  toggleMcpServer,
  type McpServer,
} from '../services/mcpApi';

export type { McpServer };

function statusDotClass(status: McpServer['status']): string {
  if (status === 'connected') return 'bg-emerald-500';
  if (status === 'reconnecting') return 'bg-amber-400';
  return 'bg-rose-500';
}

function statusLabel(status: McpServer['status']): string {
  if (status === 'connected') return 'Online';
  if (status === 'reconnecting') return 'Configured';
  return 'Offline';
}

function statusTextClass(status: McpServer['status']): string {
  if (status === 'connected') return 'text-emerald-700';
  if (status === 'reconnecting') return 'text-amber-700';
  return 'text-rose-600';
}

export const McpServerHub: React.FC = () => {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [transport, setTransport] = useState<'stdio' | 'sse'>('stdio');
  const [endpoint, setEndpoint] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = await fetchMcpStatus();
      setServers(status.servers);
    } catch {
      setServers([]);
      setError('Sidecar unavailable — cannot read MCP status.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const connectedCount = servers.filter((s) => s.status === 'connected').length;
  const totalTools = servers.reduce(
    (acc, s) => acc + (s.status === 'connected' ? s.toolsCount : 0),
    0,
  );

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !endpoint.trim()) return;
    try {
      const status = await registerMcpServer({
        name: name.trim(),
        transport,
        endpoint: endpoint.trim(),
      });
      setServers(status.servers);
      setName('');
      setEndpoint('');
      setSuccessMsg('MCP server registered.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Register failed.');
    }
  };

  const handleRemove = async (id: string) => {
    if (id === 'local-fs') return;
    try {
      const status = await removeMcpServer(id);
      setServers(status.servers);
    } catch {
      setError('Failed to remove MCP server.');
    }
  };

  const handleToggle = async (server: McpServer) => {
    if (server.builtin || !server.id) return;
    const enabled = server.status === 'failed';
    try {
      const status = await toggleMcpServer(server.id, enabled);
      setServers(status.servers);
    } catch {
      setError('Failed to update MCP server.');
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white select-text">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-teal-600">terminal</span>
            <h2 className="text-base font-bold text-neutral-900 tracking-tight font-sans">MCP Server Hub</h2>
          </div>
          <p className="text-xs text-neutral-500 font-sans leading-relaxed">
            Register stdio or SSE MCP servers alongside the built-in workspace filesystem server.
            User servers persist in Application Support and connect when agents run.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-teal-50/20 border border-teal-100/70 rounded-2xl text-left">
            <span className="text-[10px] font-bold text-teal-700 tracking-wider uppercase font-mono">CONNECTED</span>
            <div className="mt-2 text-2xl font-bold font-sans text-teal-950">
              {connectedCount} <span className="text-xs font-normal text-neutral-400">/ {servers.length}</span>
            </div>
          </div>
          <div className="p-4 bg-neutral-50/50 border border-neutral-200/50 rounded-2xl text-left">
            <span className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono">MCP TOOLS</span>
            <div className="mt-2 text-2xl font-bold font-sans text-neutral-900">{totalTools}</div>
          </div>
        </div>

        {error && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">{error}</p>
        )}
        {successMsg && (
          <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">{successMsg}</p>
        )}

        <form onSubmit={(e) => void handleRegister(e)} className="p-4 bg-neutral-50/50 border border-neutral-200/60 rounded-xl space-y-3">
          <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">Register MCP Server</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Display name"
              className="px-3 py-1.5 text-xs border border-neutral-200 rounded-lg bg-white"
            />
            <select
              value={transport}
              onChange={(e) => setTransport(e.target.value as 'stdio' | 'sse')}
              className="px-3 py-1.5 text-xs border border-neutral-200 rounded-lg bg-white"
            >
              <option value="stdio">stdio</option>
              <option value="sse">sse</option>
            </select>
            <input
              type="text"
              required
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              placeholder={transport === 'sse' ? 'https://host/mcp/sse' : 'npx -y @org/mcp-server'}
              className="px-3 py-1.5 text-xs border border-neutral-200 rounded-lg bg-white font-mono md:col-span-1"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 py-1.5 bg-neutral-900 hover:bg-black text-white text-[11px] font-bold rounded-lg"
          >
            + Register Node
          </button>
        </form>

        {loading ? (
          <p className="text-xs text-neutral-400 italic">Loading MCP status…</p>
        ) : servers.length === 0 ? (
          <p className="text-xs text-neutral-400 italic">No MCP servers available.</p>
        ) : (
          <div className="border border-neutral-200/80 bg-white rounded-xl divide-y divide-neutral-150 overflow-hidden shadow-3xs">
            {servers.map((server) => (
              <div key={server.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 text-left flex-1">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className={`inline-flex rounded-full h-3 w-3 ${statusDotClass(server.status)}`} />
                    <span className="text-xs font-bold text-neutral-900 font-sans">{server.name}</span>
                    <span className="text-[8.5px] font-mono uppercase px-1.5 py-0.2 rounded font-bold bg-neutral-100 text-neutral-800">
                      {server.transport}
                    </span>
                    {server.builtin && (
                      <span className="text-[8px] font-mono uppercase text-teal-700 bg-teal-50 px-1 rounded">builtin</span>
                    )}
                  </div>
                  <p className="text-[10.5px] font-mono text-neutral-500 bg-neutral-50 px-2 py-1 rounded border border-neutral-100/55 break-all leading-normal">
                    {server.endpoint}
                  </p>
                </div>
                <div className="flex items-end md:items-center gap-3">
                  <div className="text-[10.5px] md:text-right">
                    <div className="font-mono text-neutral-400">STATUS</div>
                    <div className={`font-semibold capitalize ${statusTextClass(server.status)}`}>
                      {statusLabel(server.status)}
                    </div>
                    <div className="font-mono text-neutral-400 mt-1">TOOLS</div>
                    <div className="font-semibold text-neutral-800">
                      {server.status === 'connected' ? server.toolsCount : '—'}
                    </div>
                    <p className="text-[10px] text-neutral-400 mt-1 max-w-[180px]">{server.lastHeartbeat}</p>
                  </div>
                  {!server.builtin && (
                    <div className="flex flex-col gap-1">
                      <button
                        type="button"
                        onClick={() => void handleToggle(server)}
                        className="text-[10px] font-bold text-neutral-600 hover:text-neutral-900"
                      >
                        {server.status === 'failed' ? 'Enable' : 'Disable'}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleRemove(server.id)}
                        className="text-[10px] font-bold text-rose-600 hover:text-rose-800"
                      >
                        Remove
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="text-[10px] font-bold text-neutral-500 hover:text-neutral-800 disabled:opacity-50"
        >
          Refresh status
        </button>
      </div>
    </div>
  );
};
