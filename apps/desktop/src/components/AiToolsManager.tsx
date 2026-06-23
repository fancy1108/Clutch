import React, { useCallback, useEffect, useState } from 'react';
import {
  connectTool,
  disconnectTool,
  fetchToolsStatus,
  type AiToolStatus,
} from '../services/toolsApi';

interface AiToolsManagerProps {
  isModalStyle?: boolean;
}

export default function AiToolsManager({ isModalStyle }: AiToolsManagerProps) {
  const [tools, setTools] = useState<AiToolStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchToolsStatus();
      setTools(list);
    } catch {
      setTools([]);
      setError('Sidecar unavailable — start the orchestrator to scan local tools.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleConnect = async (id: string) => {
    setPendingId(id);
    setError(null);
    try {
      await connectTool(id);
      await refresh();
    } catch {
      setError('Failed to connect tool. Ensure the CLI is installed and Sidecar is running.');
    } finally {
      setPendingId(null);
    }
  };

  const handleDisconnect = async (id: string) => {
    setPendingId(id);
    setError(null);
    try {
      await disconnectTool(id);
      await refresh();
    } catch {
      setError('Failed to disconnect tool.');
    } finally {
      setPendingId(null);
    }
  };

  const connectedTools = tools.filter((t) => t.connected);
  const availableTools = tools.filter((t) => !t.connected);

  return (
    <div className="flex flex-col h-full overflow-y-auto bg-white">
      <header className={`sticky top-0 z-20 bg-white/95 backdrop-blur py-5 flex items-center justify-between border-b border-neutral-100 pl-8 ${isModalStyle ? 'pr-14' : 'pr-8'}`}>
        <div className="text-left">
          <h2 className="text-sm font-bold text-neutral-800 tracking-tight font-sans">AI Tools Integration</h2>
          <p className="text-[11px] text-neutral-400 mt-0.5">
            Detected local CLIs on this machine. Connect only tools you want Clutch to use.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="text-[10px] font-bold text-neutral-500 hover:text-neutral-800 disabled:opacity-50"
        >
          Rescan
        </button>
      </header>

      <div className="p-8 space-y-8 max-w-4xl mx-auto w-full">
        {error && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {loading ? (
          <p className="text-xs text-neutral-400 italic">Scanning local toolchains…</p>
        ) : tools.length === 0 ? (
          <div className="text-left space-y-2">
            <p className="text-xs text-neutral-500">No supported CLI tools detected on this machine.</p>
            <p className="text-[11px] text-neutral-400">
              Install <span className="font-mono">claude</span> (Claude Code) or{' '}
              <span className="font-mono">Cursor</span>, then rescan.
            </p>
          </div>
        ) : (
          <>
            <section className="text-left">
              <h3 className="text-xs font-bold text-neutral-900 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                Connected
              </h3>
              {connectedTools.length === 0 ? (
                <p className="text-xs text-neutral-400 italic">No AI tools connected yet.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {connectedTools.map((tool) => (
                    <div key={tool.id} className="p-4 border border-neutral-200/60 rounded-xl bg-white shadow-xs flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center flex-shrink-0">
                        <span className="material-symbols-outlined text-neutral-600">{tool.icon}</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="text-xs font-bold text-neutral-800">{tool.name}</h4>
                        <p className="text-[10px] text-neutral-500 mt-1 leading-relaxed">{tool.description}</p>
                        <div className="mt-3">
                          <button
                            type="button"
                            onClick={() => void handleDisconnect(tool.id)}
                            disabled={pendingId === tool.id}
                            className="text-[10px] font-semibold text-neutral-400 hover:text-red-500 transition-colors disabled:opacity-50"
                          >
                            {pendingId === tool.id ? 'Disconnecting…' : 'Disconnect'}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="text-left">
              <h3 className="text-xs font-bold text-neutral-900 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-neutral-300"></span>
                Detected (not connected)
              </h3>
              {availableTools.length === 0 ? (
                <p className="text-xs text-neutral-400 italic">All detected tools are connected.</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {availableTools.map((tool) => (
                    <div key={tool.id} className="p-4 border border-dashed border-neutral-200 rounded-xl bg-neutral-50/50 flex items-start gap-4">
                      <div className="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center flex-shrink-0 opacity-60">
                        <span className="material-symbols-outlined text-neutral-500">{tool.icon}</span>
                      </div>
                      <div className="flex-1">
                        <h4 className="text-xs font-bold text-neutral-600">{tool.name}</h4>
                        <p className="text-[10px] text-neutral-400 mt-1 leading-relaxed">{tool.description}</p>
                        <div className="mt-3">
                          <button
                            type="button"
                            onClick={() => void handleConnect(tool.id)}
                            disabled={pendingId === tool.id}
                            className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-900 text-white text-[10px] font-bold rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                          >
                            {pendingId === tool.id ? 'Connecting…' : 'Connect Tool'}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
