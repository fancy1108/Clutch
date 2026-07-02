import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { useLanguage } from './LanguageContext';
import { BTN_ICON_SM } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import type { ClutchRunStatus } from '../types';
import { clutchStore } from '../services/clutchState';

interface ChatTerminalViewProps {
  visible: boolean;
  terminalLogs: string[];
  clutchStatus: ClutchRunStatus;
  shellSessionStatus?: string;
  activeAgentName?: string;
  engineHint?: string;
  cliTool: string;
  sessionRunId: string;
  onClearTerminal?: () => void;
}

function logColorClass(log: string): string {
  if (log.includes('error') || log.includes('reject') || log.includes('FAILED')) {
    return 'text-rose-400 font-semibold';
  }
  if (log.includes('SUCCESS') || log.includes('PASSED')) {
    return 'text-emerald-400 font-bold';
  }
  if (log.includes('WARN') || log.includes('WARNING')) {
    return 'text-amber-400';
  }
  if (log.includes('SUPERVISOR') || log.includes('[HYBRID]')) {
    return 'text-amber-200';
  }
  return 'text-neutral-300';
}

function isPtyLiveStatus(status: string): boolean {
  return status === 'ready' || status === 'booting';
}

export const ChatTerminalView: React.FC<ChatTerminalViewProps> = ({
  visible,
  terminalLogs,
  clutchStatus,
  shellSessionStatus,
  activeAgentName,
  engineHint,
  cliTool,
  sessionRunId,
  onClearTerminal,
}) => {
  const { t } = useLanguage();
  const hostRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const attachTokenRef = useRef(0);
  const visibleRef = useRef(visible);
  const attachedKeyRef = useRef<string | null>(null);
  const [ptyStatus, setPtyStatus] = useState('');
  const [connectPhase, setConnectPhase] = useState<'idle' | 'connecting' | 'ready' | 'failed'>('idle');
  const [useLogFallback, setUseLogFallback] = useState(false);
  const isActive = clutchStatus === 'running' || clutchStatus === 'awaiting_human';

  visibleRef.current = visible;

  const refreshTerminalLayout = () => {
    const term = termRef.current;
    const fitAddon = fitRef.current;
    if (!term || !fitAddon) return;
    fitAddon.fit();
    void clutchStore.sendPtyResize(term.cols, term.rows);
    term.focus();
  };

  // Initialize xterm once; keep alive across chat/terminal visibility toggles.
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: 'JetBrains Mono, Menlo, monospace',
      fontSize: 12,
      theme: {
        background: '#111111',
        foreground: '#d4d4d4',
        cursor: '#f5f5f5',
      },
      convertEol: true,
    });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(host);
    fitAddon.fit();
    termRef.current = term;
    fitRef.current = fitAddon;

    const resizeObserver = new ResizeObserver(() => {
      fitAddon.fit();
      if (visibleRef.current) {
        void clutchStore.sendPtyResize(term.cols, term.rows);
      }
    });
    resizeObserver.observe(host);

    const unsubOutput = clutchStore.onPtyOutput((chunk) => {
      term.write(chunk);
      if (visibleRef.current) {
        setConnectPhase((phase) => (phase === 'connecting' ? 'ready' : phase));
      }
    });
    const unsubStatus = clutchStore.onPtyStatusChange((status) => {
      setPtyStatus(status);
      if (status === 'ready') {
        if (visibleRef.current) {
          setConnectPhase('ready');
          refreshTerminalLayout();
        }
      } else if (status === 'blocked' || status === 'exited') {
        setConnectPhase('failed');
        setUseLogFallback(true);
      }
    });

    term.onData((data) => {
      if (visibleRef.current) {
        void clutchStore.sendPtyInput(data);
      }
    });

    return () => {
      unsubOutput();
      unsubStatus();
      resizeObserver.disconnect();
      void clutchStore.detachInteractivePty();
      attachedKeyRef.current = null;
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, []);

  // Attach when terminal tab is shown; keep PTY alive while hidden in chat mode.
  useEffect(() => {
    if (!visible || useLogFallback) {
      return;
    }

    const attachKey = `${sessionRunId}:${cliTool}`;
    const token = ++attachTokenRef.current;
    const alreadyAttached =
      attachedKeyRef.current === attachKey && isPtyLiveStatus(clutchStore.ptySessionStatus);

    if (alreadyAttached) {
      setConnectPhase('ready');
      setPtyStatus(clutchStore.ptySessionStatus || 'ready');
      refreshTerminalLayout();
      return;
    }

    setConnectPhase('connecting');

    const attach = async () => {
      try {
        await clutchStore.connect(sessionRunId);
        if (token !== attachTokenRef.current) return;

        if (attachedKeyRef.current && attachedKeyRef.current !== attachKey) {
          await clutchStore.detachInteractivePty();
          if (token !== attachTokenRef.current) return;
          termRef.current?.reset();
        }

        await clutchStore.attachInteractivePty(cliTool);
        if (token !== attachTokenRef.current) return;

        attachedKeyRef.current = attachKey;
        const term = termRef.current;
        const fitAddon = fitRef.current;
        if (term && fitAddon) {
          fitAddon.fit();
          void clutchStore.sendPtyResize(term.cols, term.rows);
          term.focus();
        }

        if (isPtyLiveStatus(clutchStore.ptySessionStatus)) {
          setConnectPhase('ready');
        }
      } catch {
        if (token === attachTokenRef.current) {
          setConnectPhase('failed');
          setUseLogFallback(true);
        }
      }
    };

    void attach();

    return () => {
      attachTokenRef.current += 1;
    };
  }, [visible, cliTool, sessionRunId, useLogFallback]);

  const statusLabel = connectPhase === 'connecting'
    ? t('Connecting interactive CLI…')
    : ptyStatus === 'ready' || connectPhase === 'ready'
      ? t('Interactive CLI ready')
      : shellSessionStatus === 'queued_pool'
        ? t('Queued for shell...')
        : isActive
          ? t('Receiving sidecar events')
          : t('SIDECAR IDLE');

  if (useLogFallback) {
    return (
      <div
        data-testid="chat-terminal-view"
        className="w-full max-w-4xl mx-auto flex flex-col min-h-[calc(100vh-220px)]"
      >
        <div className="flex items-center justify-between gap-3 mb-3 px-1">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
              {t('Terminal console')}
            </p>
            <p className="text-[11px] text-on-surface-variant/80 truncate mt-0.5">
              {t('Read-only audit log (interactive PTY unavailable)')}
            </p>
          </div>
          <button
            type="button"
            data-testid="chat-terminal-clear-btn"
            onClick={() => onClearTerminal?.()}
            className={`${BTN_ICON_SM} text-on-surface-variant hover:text-on-surface`}
            aria-label={t('Clear')}
          >
            <LegacyIcon name="restart_alt" className="text-[14px]" />
          </button>
        </div>
        <div className="flex-1 rounded-2xl border border-neutral-800 bg-[#111111] p-4 font-mono text-[11px] overflow-y-auto">
          {terminalLogs.length === 0 ? (
            <p className="text-neutral-500 font-sans text-[12px]">{t('No terminal logs yet')}</p>
          ) : (
            terminalLogs.map((log, index) => (
              <div key={`${index}-${log.slice(0, 24)}`} className={`mb-1 ${logColorClass(log)}`}>
                <span className="text-neutral-600 select-none mr-1.5">$</span>
                {log}
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="chat-terminal-view"
      className="w-full max-w-4xl mx-auto flex flex-col min-h-[calc(100vh-220px)]"
    >
      <div className="flex items-center justify-between gap-3 mb-3 px-1">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
            {t('Terminal console')}
          </p>
          <p className="text-[11px] text-on-surface-variant/80 truncate mt-0.5">
            {activeAgentName || t('Clutch Agent')}
            {engineHint ? ` · ${engineHint}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="hidden sm:flex items-center gap-1.5 text-[10px] font-mono text-on-surface-variant bg-surface-container-low border border-outline-variant/30 px-2 py-1 rounded-lg">
            {connectPhase === 'connecting' ? (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            ) : connectPhase === 'ready' || ptyStatus === 'ready' ? (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            ) : (
              <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
            )}
            {statusLabel}
          </span>
        </div>
      </div>

      <div className="relative flex-1 rounded-2xl border border-neutral-800 bg-[#111111] shadow-md overflow-hidden flex flex-col min-h-[420px]">
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-neutral-800 bg-[#1a1a1a]">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500/90" />
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400/90" />
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/90" />
          <span className="ml-2 text-[10px] font-mono text-neutral-500 truncate">
            clutch — {engineHint || cliTool}
          </span>
        </div>
        <div ref={hostRef} className="flex-1 min-h-[360px] p-1" />
        {connectPhase === 'connecting' ? (
          <div className="absolute inset-x-0 bottom-0 top-10 flex items-center justify-center bg-[#111111]/80 pointer-events-none">
            <p className="text-xs font-mono text-neutral-400 animate-pulse">
              {t('Connecting interactive CLI…')}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
};
