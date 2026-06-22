import React, { useState } from 'react';

export interface McpServer {
  id: string;
  name: string;
  type: 'local' | 'remote';
  transport: 'stdio' | 'sse' | 'websocket';
  endpoint: string;
  status: 'connected' | 'reconnecting' | 'failed';
  latency: number; // in ms
  toolsCount: number;
  lastHeartbeat: string;
}

export const McpServerHub: React.FC = () => {
  const [servers, setServers] = useState<McpServer[]>([
    {
      id: 'local-fs',
      name: 'Local Filesystem MCP Server',
      type: 'local',
      transport: 'stdio',
      endpoint: 'npx -y @modelcontextprotocol/server-filesystem /workspace',
      status: 'connected',
      latency: 4,
      toolsCount: 5,
      lastHeartbeat: 'Just now'
    },
    {
      id: 'postgresql-db',
      name: 'PostgreSQL Relational DB Sandbox',
      type: 'remote',
      transport: 'sse',
      endpoint: 'http://localhost:5432/mcp-gateway',
      status: 'connected',
      latency: 32,
      toolsCount: 8,
      lastHeartbeat: '2s ago'
    },
    {
      id: 'figma-spec',
      name: 'Figma Api Spec Extraction Server',
      type: 'remote',
      transport: 'sse',
      endpoint: 'https://api.figma.com/v1/mcp',
      status: 'connected',
      latency: 56,
      toolsCount: 4,
      lastHeartbeat: 'Just now'
    },
    {
      id: 'slack-comms',
      name: 'Slack Webhook Feed Connector',
      type: 'remote',
      transport: 'websocket',
      endpoint: 'wss://slack.com/mcp-notifications',
      status: 'reconnecting',
      latency: 0,
      toolsCount: 2,
      lastHeartbeat: 'Connection lost (Retrying...)'
    },
    {
      id: 'google-docs-core',
      name: 'Google Sheets & Workspace Core Sync',
      type: 'remote',
      transport: 'sse',
      endpoint: 'https://mcp-sheets.googleworkspace.com',
      status: 'connected',
      latency: 42,
      toolsCount: 6,
      lastHeartbeat: 'Just now'
    }
  ]);

  const [newServerName, setNewServerName] = useState('');
  const [newServerType, setNewServerType] = useState<'local' | 'remote'>('local');
  const [newServerEndpoint, setNewServerEndpoint] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);

  const handleRegisterServer = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newServerName.trim() || !newServerEndpoint.trim()) return;

    const newServer: McpServer = {
      id: `custom-mcp-${Date.now()}`,
      name: newServerName.trim(),
      type: newServerType,
      transport: newServerType === 'local' ? 'stdio' : 'sse',
      endpoint: newServerEndpoint.trim(),
      status: 'connected',
      latency: Math.floor(Math.random() * 80) + 12,
      toolsCount: Math.floor(Math.random() * 6) + 2,
      lastHeartbeat: 'Just now'
    };

    setServers([...servers, newServer]);
    setNewServerName('');
    setNewServerEndpoint('');
    setIsFormOpen(false);
  };

  const handleToggleStatus = (id: string) => {
    setServers(prev => prev.map(s => {
      if (s.id === id) {
        const nextStatus = s.status === 'connected' ? 'failed' : s.status === 'failed' ? 'reconnecting' : 'connected';
        return {
          ...s,
          status: nextStatus,
          latency: nextStatus === 'connected' ? Math.floor(Math.random() * 45) + 5 : 0,
          lastHeartbeat: nextStatus === 'connected' ? 'Just now' : 'Reconnecting timeout'
        };
      }
      return s;
    }));
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white select-text">
      {/* Scrollable Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        
        {/* Banner Headers */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-teal-600">terminal</span>
            <h2 className="text-base font-bold text-neutral-900 tracking-tight font-sans">MCP Server Hub</h2>
          </div>
          <p className="text-xs text-neutral-500 font-sans leading-relaxed">
            Monitor, connect, and configure Model Context Protocol (MCP) servers locally or worldwide. Connected servers expose custom workspace-driven capabilities to your operational agents.
          </p>
        </div>

        {/* Section 1: Dashboard Connectivity Indicators Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-teal-50/20 border border-teal-100/70 rounded-2xl flex flex-col justify-between text-left">
            <span className="text-[10px] font-bold text-teal-700 tracking-wider uppercase font-mono">STATUS INTEGRATED</span>
            <div className="mt-2 text-2xl font-bold font-sans text-teal-950 flex items-baseline gap-1.5">
              <span>{servers.filter(s => s.status === 'connected').length}</span>
              <span className="text-xs font-normal text-neutral-400">/ {servers.length} Alive</span>
            </div>
            <p className="text-[9.5px]/snug text-teal-600 mt-1">Ready for orchestration pipelines.</p>
          </div>

          <div className="p-4 bg-neutral-50/50 border border-neutral-200/50 rounded-2xl flex flex-col justify-between text-left">
            <span className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono">TOTAL MCP FUNCTIONS</span>
            <div className="mt-2 text-2xl font-bold font-sans text-neutral-900">
              {servers.reduce((acc, s) => acc + (s.status === 'connected' ? s.toolsCount : 0), 0)}
            </div>
            <p className="text-[9.5px]/snug text-neutral-400 mt-1">Mounted system context tools.</p>
          </div>

          <div className="p-4 bg-neutral-50/50 border border-neutral-200/50 rounded-2xl flex flex-col justify-between text-left">
            <span className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono">AVERAGE PING LATENCY</span>
            <div className="mt-2 text-2xl font-bold font-mono text-neutral-900">
              {Math.round(servers.filter(s => s.status === 'connected').reduce((acc, s) => acc + s.latency, 0) / (servers.filter(s => s.status === 'connected').length || 1))}ms
            </div>
            <p className="text-[9.5px]/snug text-neutral-400 mt-1">Optimal local runtime sockets.</p>
          </div>
        </div>

        {/* MCP Servers List Card Column with Heatbeat lights */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">Active Context Registry Connections</h3>
            <button
              onClick={() => setIsFormOpen(!isFormOpen)}
              className="px-2.5 py-1 bg-neutral-900 hover:bg-black text-white text-[10.5px] font-bold rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <span className="material-symbols-outlined text-[13px]">add</span>
              Add Connection
            </button>
          </div>

          {isFormOpen && (
            <form onSubmit={handleRegisterServer} className="bg-neutral-50/50 border border-neutral-200 p-4 rounded-xl space-y-3 animate-fade-in text-left">
              <h4 className="text-[10.5px] font-extrabold font-mono uppercase text-neutral-800 pb-1.5 border-b border-neutral-200/45">Connect New MCP Server</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="grid grid-cols-1 gap-1">
                  <label className="text-[9.5px] font-bold text-neutral-500 uppercase font-mono">Server Connection Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. SQLite Read-Write Gate"
                    value={newServerName}
                    onChange={(e) => setNewServerName(e.target.value)}
                    className="px-3 py-1.5 text-xs border border-neutral-200 bg-white rounded-lg focus:outline-none"
                  />
                </div>
                <div className="grid grid-cols-1 gap-1">
                  <label className="text-[9.5px] font-bold text-neutral-500 uppercase font-mono">Isolation Level / Type</label>
                  <select
                    value={newServerType}
                    onChange={(e) => setNewServerType(e.target.value as 'local' | 'remote')}
                    className="px-3 py-1.5 text-xs border border-neutral-200 bg-white rounded-lg focus:outline-none"
                  >
                    <option value="local">Local Instance (Fast execution)</option>
                    <option value="remote">Remote Microservice (API proxy)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-1">
                <label className="text-[9.5px] font-bold text-neutral-500 uppercase font-mono">Host Executable Path / SSE Endpoint</label>
                <input
                  type="text"
                  required
                  placeholder={newServerType === 'local' ? "e.g. npx -y @modelcontextprotocol/server-sqlite --db /data.db" : "https://mcp-gateway.domain.com/sse"}
                  value={newServerEndpoint}
                  onChange={(e) => setNewServerEndpoint(e.target.value)}
                  className="px-3 py-1.5 text-xs border border-neutral-200 bg-white rounded-lg font-mono focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsFormOpen(false)}
                  className="px-3 py-1 bg-white hover:bg-neutral-100 border border-neutral-200 rounded-lg text-xs font-semibold text-neutral-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4.5 py-1 bg-neutral-900 hover:bg-black text-white rounded-lg text-xs font-bold"
                >
                  Connect Server
                </button>
              </div>
            </form>
          )}

          <div className="border border-neutral-200/80 bg-white rounded-xl divide-y divide-neutral-150 overflow-hidden shadow-3xs">
            {servers.map(server => (
              <div key={server.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                
                {/* Server specifications & state */}
                <div className="space-y-1.5 text-left">
                  <div className="flex items-center gap-2.5">
                    {/* Live Heartbeat Indicator Light */}
                    <div className="relative flex h-3 w-3">
                      {server.status === 'connected' && (
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      )}
                      <span className={`relative inline-flex rounded-full h-3 w-3 ${
                        server.status === 'connected'
                          ? 'bg-emerald-500'
                          : server.status === 'reconnecting'
                          ? 'bg-amber-500 animate-pulse'
                          : 'bg-rose-500'
                      }`}></span>
                    </div>

                    <span className="text-xs font-bold text-neutral-900 font-sans">{server.name}</span>
                    <span className={`text-[8.5px] font-mono uppercase px-1.5 py-0.2 rounded font-bold ${
                      server.type === 'local' ? 'bg-neutral-100 text-neutral-800' : 'bg-neutral-100 text-neutral-500'
                    }`}>
                      {server.type}
                    </span>
                  </div>

                  <p className="text-[10.5px] font-mono text-neutral-500 bg-neutral-50 px-2 py-1 rounded border border-neutral-100/55 break-all leading-normal">
                    {server.endpoint}
                  </p>
                </div>

                {/* Status signals indicators */}
                <div className="flex items-center gap-5 justify-between md:justify-end flex-shrink-0">
                  <div className="grid grid-cols-2 md:grid-cols-1 gap-y-1 md:text-right text-[10.5px]">
                    <div className="font-mono text-neutral-400">STATUS</div>
                    <div className={`font-semibold capitalize text-right md:-mt-1 ${
                      server.status === 'connected'
                        ? 'text-emerald-700'
                        : server.status === 'reconnecting'
                        ? 'text-amber-700'
                        : 'text-rose-600 font-bold'
                    }`}>
                      {server.status === 'connected' ? '🟢 Online' : server.status === 'reconnecting' ? '⚡ Reconnecting' : '🔴 Offline'}
                    </div>

                    <div className="font-mono text-neutral-400">PING / POWER</div>
                    <div className="font-semibold text-neutral-800 text-right md:-mt-1">
                      {server.status === 'connected' ? `${server.latency}ms (${server.toolsCount} Tools)` : '—'}
                    </div>
                  </div>

                  <button
                    onClick={() => handleToggleStatus(server.id)}
                    className="px-2.5 py-1.5 bg-neutral-50 hover:bg-neutral-100/80 border border-neutral-200/70 rounded-lg text-[10px] font-bold font-mono text-neutral-600 hover:text-neutral-900 flex items-center justify-center gap-1 transition-all"
                    title="Simulate service heartbeat check"
                  >
                    <span className="material-symbols-outlined text-[12px]">cycle</span>
                    Poke Hub
                  </button>
                </div>

              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};
