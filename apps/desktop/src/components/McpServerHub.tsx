import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchMcpStatus,
  registerMcpServer,
  removeMcpServer,
  toggleMcpServer,
  saveMcpConfig,
  importClaudeMcp,
  type McpServer,
} from '../services/mcpApi';
import { BTN_GHOST, BTN_PRIMARY } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { ALERT_SUCCESS, ALERT_WARNING } from './ui/surfaceStyles';

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
  const [isJsonEditMode, setIsJsonEditMode] = useState(false);
  const [rawJsonConfig, setRawJsonConfig] = useState('');


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

  const handleSaveJsonConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const parsed = JSON.parse(rawJsonConfig);
      if (!Array.isArray(parsed)) {
        throw new Error('Config must be a JSON array of server configurations.');
      }
      const status = await saveMcpConfig(parsed);
      setServers(status.servers);
      setIsJsonEditMode(false);
      setSuccessMsg('MCP raw config saved.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'Save JSON failed. Please verify syntax.');
    }
  };

  const handleImportClaude = async () => {
    setError(null);
    try {
      const status = await importClaudeMcp();
      setServers(status.servers);
      setSuccessMsg('Imported configurations from local Claude setups.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err: any) {
      setError(err instanceof Error ? err.message : 'Import from Claude failed.');
    }
  };


  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white select-text">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <LegacyIcon name="terminal" className="text-[20px] text-emerald-600" />
            <h2 className="text-base font-bold text-neutral-900 tracking-tight font-sans">MCP Server Hub</h2>
          </div>
          <p className="text-xs text-neutral-500 font-sans leading-relaxed">
            Register stdio or SSE MCP servers alongside the built-in workspace filesystem server.
            User servers persist in Application Support and connect when agents run.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-emerald-50/20 border border-emerald-100/70 rounded-2xl text-left">
            <span className="text-[10px] font-bold text-emerald-700 tracking-wider uppercase font-mono">CONNECTED</span>
            <div className="mt-2 text-2xl font-bold font-sans text-neutral-900">
              {connectedCount} <span className="text-xs font-normal text-neutral-400">/ {servers.length}</span>
            </div>
          </div>
          <div className="p-4 bg-neutral-50/50 border border-neutral-200/50 rounded-2xl text-left">
            <span className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono">MCP TOOLS</span>
            <div className="mt-2 text-2xl font-bold font-sans text-neutral-900">{totalTools}</div>
          </div>
        </div>

        {error && (
          <p className={ALERT_WARNING}>{error}</p>
        )}
        {successMsg && (
          <p className={ALERT_SUCCESS}>{successMsg}</p>
        )}

        {isJsonEditMode ? (
          <form onSubmit={(e) => void handleSaveJsonConfig(e)} className="p-4 bg-neutral-50/50 border border-neutral-200/60 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">Edit Raw Config JSON</h3>
              <button
                type="button"
                onClick={() => setIsJsonEditMode(false)}
                className={`${BTN_GHOST} text-[10px] font-bold`}
              >
                Cancel
              </button>
            </div>
            <textarea
              required
              rows={8}
              value={rawJsonConfig}
              onChange={(e) => setRawJsonConfig(e.target.value)}
              placeholder='[ { "name": "Git Tools", "transport": "stdio", "endpoint": "..." } ]'
              className="w-full p-3 text-xs border border-neutral-200 rounded-lg bg-white font-mono"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                className={BTN_PRIMARY}
              >
                Save JSON Config
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={(e) => void handleRegister(e)} className="p-4 bg-neutral-50/50 border border-neutral-200/60 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">Register MCP Server</h3>
              <div className="flex gap-2.5 items-center">
                <button
                  type="button"
                  onClick={() => void handleImportClaude()}
                  className={`${BTN_GHOST} text-[10px] font-bold text-emerald-700 hover:text-emerald-900 border-transparent hover:bg-emerald-50`}
                >
                  Import from Claude
                </button>
                <span className="text-neutral-300 text-[10px]">|</span>
                <button
                  type="button"
                  onClick={() => {
                    setRawJsonConfig(JSON.stringify(servers.filter(s => !s.builtin).map(s => ({
                      id: s.id,
                      name: s.name,
                      transport: s.transport,
                      endpoint: s.endpoint,
                      enabled: s.enabled ?? true
                    })), null, 2));
                    setIsJsonEditMode(true);
                  }}
                  className={`${BTN_GHOST} text-[10px] font-bold`}
                >
                  Edit raw JSON
                </button>
              </div>
            </div>
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
              className={BTN_PRIMARY}
            >
              + Register Node
            </button>
          </form>
        )}

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
                      <span className="text-[8px] font-mono uppercase text-emerald-700 bg-emerald-50 px-1 rounded">builtin</span>
                    )}
                  </div>
                  <p className="text-[10.5px] font-mono text-neutral-500 bg-neutral-50 px-2 py-1 rounded border border-neutral-100/55 break-all leading-normal">
                    {server.endpoint}
                  </p>
                  {server.tools && server.tools.length > 0 && (
                    <div className="mt-2 pl-3 border-l-2 border-emerald-500/30 space-y-1 select-text">
                      <span className="text-[9px] font-extrabold text-neutral-400 font-mono tracking-wider uppercase block">Exposed Tools:</span>
                      <div className="flex flex-col gap-1 max-h-32 overflow-y-auto pr-1">
                        {server.tools.map((t, idx) => (
                          <div key={idx} className="text-[10px] text-neutral-600 font-mono flex flex-wrap items-center gap-1.5 leading-snug">
                            <span className="font-extrabold text-emerald-800 bg-emerald-50 px-1 rounded text-[9px]">{t.name}</span>
                            <span className="text-neutral-400 font-sans text-[9px] truncate max-w-[320px]" title={t.description}>{t.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
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
          className={`${BTN_GHOST} text-[10px] font-bold disabled:opacity-50`}
        >
          Refresh status
        </button>
      </div>
    </div>
  );
};
