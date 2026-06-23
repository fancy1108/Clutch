import React from 'react';

interface TerminalPanelProps {
  terminalLogs: string[];
  isActive?: boolean;
}

export const TerminalPanel: React.FC<TerminalPanelProps> = ({ terminalLogs, isActive = false }) => {
  return (
    <div className="flex-1 overflow-y-auto p-4 bg-[#111111] text-green-500 font-mono text-[11px] leading-6 break-words tracking-tight pb-32">
      <div className="mb-4 text-neutral-400 font-sans tracking-wide text-[10px] select-none flex justify-between items-center bg-[#222222] p-2 rounded-lg border border-neutral-800">
        <span className="flex items-center gap-1.5">
          {isActive ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" /> SIDECAR ACTIVE
            </>
          ) : (
            <>SIDECAR IDLE</>
          )}
        </span>
        <span 
          className="material-symbols-outlined text-[13px] cursor-pointer hover:text-white transition-colors" 
          onClick={() => console.warn("Terminal clears and restarts outputs logs.")}
        >
          restart_alt
        </span>
      </div>
      {terminalLogs.map((log, i) => {
        const cls = log.includes('error') || log.includes('reject') || log.includes('failed') ? 'text-rose-500 font-bold' 
          : log.includes('SUCCESS') || log.includes('PASS') ? 'text-emerald-400 font-bold'
          : log.includes('WARN') ? 'text-amber-400'
          : log.includes('SUPERVISOR') ? 'text-amber-300 font-bold'
          : 'text-neutral-300';
        return (
          <div key={i} className={`mb-1 ${cls}`}>
            {log}
          </div>
        );
      })}
      <div className="mt-2 text-neutral-500 animate-pulse">_</div>
    </div>
  );
};
