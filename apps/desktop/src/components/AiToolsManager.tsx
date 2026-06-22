import React, { useState } from 'react';

interface AiTool {
  id: string;
  name: string;
  description: string;
  icon: string;
  status: 'connected' | 'available';
}

const INITIAL_TOOLS: AiTool[] = [
  {
    id: 'claude-cli',
    name: 'Claude Code CLI',
    description: 'Use Claude seamlessly from your terminal. Great for system scripting and bash commands.',
    icon: 'terminal',
    status: 'connected',
  },
  {
    id: 'antigravity-cli',
    name: 'Antigravity CLI',
    description: 'Direct deep integrations with local file systems and Antigravity core engines.',
    icon: 'rocket_launch',
    status: 'connected',
  },
  {
    id: 'cursor',
    name: 'Cursor',
    description: 'AI-first code editor integration, directly linking your workspace via local IPC.',
    icon: 'edit_document',
    status: 'available',
  },
  {
    id: 'code-x',
    name: 'Code X',
    description: 'Deep source-code analysis and cross-repository structural manipulation agent.',
    icon: 'code_blocks',
    status: 'available',
  },
];

interface AiToolsManagerProps {
  isModalStyle?: boolean;
}

export default function AiToolsManager({ isModalStyle }: AiToolsManagerProps) {
  const [tools, setTools] = useState<AiTool[]>(INITIAL_TOOLS);

  const handleConnect = (id: string) => {
    setTools(prev =>
      prev.map(tool =>
        tool.id === id ? { ...tool, status: 'connected' } : tool
      )
    );
  };

  const handleDisconnect = (id: string) => {
    setTools(prev =>
      prev.map(tool =>
        tool.id === id ? { ...tool, status: 'available' } : tool
      )
    );
  };

  const connectedTools = tools.filter(t => t.status === 'connected');
  const availableTools = tools.filter(t => t.status === 'available');

  return (
    <div className="flex flex-col h-full overflow-y-auto bg-white">
      {/* Header */}
      <header className={`sticky top-0 z-20 bg-white/95 backdrop-blur py-5 flex items-center justify-between border-b border-neutral-100 pl-8 ${isModalStyle ? 'pr-14' : 'pr-8'}`}>
        <div className="text-left">
          <h2 className="text-sm font-bold text-neutral-800 tracking-tight font-sans">AI Tools Integration</h2>
          <p className="text-[11px] text-neutral-400 mt-0.5">
            Manage your agent orchestration environments and local toolchains.
          </p>
        </div>
      </header>

      <div className="p-8 space-y-8 max-w-4xl mx-auto w-full">
        {/* Connected Section */}
        <section className="text-left">
          <h3 className="text-xs font-bold text-neutral-900 mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Connected
          </h3>
          {connectedTools.length === 0 ? (
            <p className="text-xs text-neutral-400 italic">No AI tools currently connected.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {connectedTools.map(tool => (
                <div key={tool.id} className="p-4 border border-neutral-200/60 rounded-xl bg-white shadow-xs flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                    <span className="material-symbols-outlined text-indigo-500">{tool.icon}</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="text-xs font-bold text-neutral-800">{tool.name}</h4>
                    <p className="text-[10px] text-neutral-500 mt-1 leading-relaxed">{tool.description}</p>
                    <div className="mt-3">
                      <button
                        onClick={() => handleDisconnect(tool.id)}
                        className="text-[10px] font-semibold text-neutral-400 hover:text-red-500 transition-colors"
                      >
                        Disconnect
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Available Section */}
        <section className="text-left">
          <h3 className="text-xs font-bold text-neutral-900 mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-neutral-300"></span>
            Available
          </h3>
          {availableTools.length === 0 ? (
            <p className="text-xs text-neutral-400 italic">All available tools are connected.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {availableTools.map(tool => (
                <div key={tool.id} className="p-4 border border-dashed border-neutral-200 rounded-xl bg-neutral-50/50 flex items-start gap-4">
                  <div className="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center flex-shrink-0 opacity-60">
                    <span className="material-symbols-outlined text-neutral-500">{tool.icon}</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="text-xs font-bold text-neutral-600">{tool.name}</h4>
                    <p className="text-[10px] text-neutral-400 mt-1 leading-relaxed">{tool.description}</p>
                    <div className="mt-3">
                      <button
                        onClick={() => handleConnect(tool.id)}
                        className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-900 text-white text-[10px] font-bold rounded-lg transition-colors cursor-pointer"
                      >
                        Connect Tool
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
