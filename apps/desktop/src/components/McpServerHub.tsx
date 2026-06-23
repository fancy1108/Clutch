import React, { useCallback, useEffect, useState } from 'react';
import { fetchMcpStatus } from '../services/modelsApi';

export interface McpServer {
  id: string;
  name: string;
  type: 'local' | 'remote';
  transport: 'stdio' | 'sse' | 'websocket';
  endpoint: string;
  status: 'connected' | 'reconnecting' | 'failed';
  toolsCount: number;
  lastHeartbeat: string;
}

export const McpServerHub: React.FC = () => {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = await fetchMcpStatus();
      const fs = status.filesystem;
      const workspacePath = fs.workspace_path ?? '(no workspace authorized)';
      setServers([
        {
          id: 'local-fs',
          name: 'Local Filesystem MCP Server',
          type: 'local',
          transport: 'stdio',
          endpoint: `npx -y @modelcontextprotocol/server-filesystem ${workspacePath}`,
          status: fs.connected ? 'connected' : 'failed',
          toolsCount: fs.tools,
          lastHeartbeat: fs.connected ? 'Workspace authorized' : 'Authorize a workspace first',
        },
      ]);
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

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white select-text">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-teal-600">terminal</span>
            <h2 className="text-base font-bold text-neutral-900 tracking-tight font-sans">MCP Server Hub</h2>
          </div>
          <p className="text-xs text-neutral-500 font-sans leading-relaxed">
            Clutch MVP exposes the workspace filesystem MCP when a workspace is authorized. Additional MCP servers are not yet supported.
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

        {loading ? (
          <p className="text-xs text-neutral-400 italic">Loading MCP status…</p>
        ) : servers.length === 0 ? (
          <p className="text-xs text-neutral-400 italic">No MCP servers available.</p>
        ) : (
          <div className="border border-neutral-200/80 bg-white rounded-xl divide-y divide-neutral-150 overflow-hidden shadow-3xs">
            {servers.map((server) => (
              <div key={server.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 text-left">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`inline-flex rounded-full h-3 w-3 ${
                        server.status === 'connected' ? 'bg-emerald-500' : 'bg-rose-500'
                      }`}
                    />
                    <span className="text-xs font-bold text-neutral-900 font-sans">{server.name}</span>
                    <span className="text-[8.5px] font-mono uppercase px-1.5 py-0.2 rounded font-bold bg-neutral-100 text-neutral-800">
                      {server.type}
                    </span>
                  </div>
                  <p className="text-[10.5px] font-mono text-neutral-500 bg-neutral-50 px-2 py-1 rounded border border-neutral-100/55 break-all leading-normal">
                    {server.endpoint}
                  </p>
                </div>
                <div className="text-[10.5px] md:text-right">
                  <div className="font-mono text-neutral-400">STATUS</div>
                  <div
                    className={`font-semibold capitalize ${
                      server.status === 'connected' ? 'text-emerald-700' : 'text-rose-600'
                    }`}
                  >
                    {server.status === 'connected' ? 'Online' : 'Offline'}
                  </div>
                  <div className="font-mono text-neutral-400 mt-1">TOOLS</div>
                  <div className="font-semibold text-neutral-800">
                    {server.status === 'connected' ? server.toolsCount : '—'}
                  </div>
                  <p className="text-[10px] text-neutral-400 mt-1">{server.lastHeartbeat}</p>
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
