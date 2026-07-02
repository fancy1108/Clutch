import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { Minimize2, CheckCircle2 } from 'lucide-react';
import { useLanguage } from '../LanguageContext';
import type { PtyLane } from '../../types';
import { clutchStore } from '../../services/clutchState';
import { resolveBrandLogoSrc } from '../../services/brandLogos';
import { agentDisplayName } from '../../services/terminalOrchestraUtils';

interface TerminalLanePaneProps {
  lane: PtyLane;
  sessionRunId: string;
  visible: boolean;
  barFocused: boolean;
  onFocusLane: (laneId: string) => void;
  onCollapseLane: (laneId: string) => void;
  onCompleteLane: (laneId: string) => void;
  paneRef?: (el: HTMLDivElement | null, laneId: string) => void;
}

function isPtyLiveStatus(status: string): boolean {
  return status === 'ready' || status === 'booting';
}

export const TerminalLanePane: React.FC<TerminalLanePaneProps> = ({
  lane,
  sessionRunId,
  visible,
  barFocused,
  onFocusLane,
  onCollapseLane,
  onCompleteLane,
  paneRef,
}) => {
  const { t } = useLanguage();
  const hostRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const attachTokenRef = useRef(0);
  const attachedKeyRef = useRef<string | null>(null);
  const [ptyStatus, setPtyStatus] = useState('');
  const [connectPhase, setConnectPhase] = useState<'idle' | 'connecting' | 'ready' | 'failed'>('idle');

  const displayName = agentDisplayName(lane.agent_type);
  const brandLogo = resolveBrandLogoSrc({ agentType: lane.agent_type });
  const isQueued = lane.status === 'queued';
  const isCompleted = lane.status === 'completed';

  const assignPaneRef = useCallback(
    (el: HTMLDivElement | null) => {
      paneRef?.(el, lane.lane_id);
    },
    [paneRef, lane.lane_id],
  );

  const refreshLayout = () => {
    const term = termRef.current;
    const fitAddon = fitRef.current;
    if (!term || !fitAddon) return;
    try {
      fitAddon.fit();
    } catch {
      return;
    }
    void clutchStore.sendPtyResize(term.cols, term.rows, lane.lane_id);
    if (!barFocused) term.focus();
  };

  useEffect(() => {
    if (!visible || isQueued || isCompleted) return;
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
    try {
      fitAddon.fit();
    } catch {
      // Host may not have dimensions yet; ResizeObserver will refit.
    }
    termRef.current = term;
    fitRef.current = fitAddon;

    const resizeObserver = new ResizeObserver(() => {
      try {
        fitAddon.fit();
      } catch {
        return;
      }
      if (visible) {
        void clutchStore.sendPtyResize(term.cols, term.rows, lane.lane_id);
      }
    });
    resizeObserver.observe(host);

    const unsubOutput = clutchStore.onPtyOutputForLane(lane.lane_id, (chunk) => {
      term.write(chunk);
      if (visible) setConnectPhase((phase) => (phase === 'connecting' ? 'ready' : phase));
    });
    const unsubStatus = clutchStore.onPtyStatusChangeForLane(lane.lane_id, (status) => {
      setPtyStatus(status);
      if (status === 'ready') {
        if (visible) {
          setConnectPhase('ready');
          refreshLayout();
        }
      } else if (status === 'blocked' || status === 'exited') {
        setConnectPhase('failed');
      }
    });

    term.onData((data) => {
      if (visible && !barFocused) {
        void clutchStore.sendPtyInput(data, lane.lane_id);
      }
    });

    return () => {
      unsubOutput();
      unsubStatus();
      resizeObserver.disconnect();
      void clutchStore.detachInteractivePty(lane.lane_id);
      attachedKeyRef.current = null;
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, [lane.lane_id, isQueued, isCompleted, visible]);

  useEffect(() => {
    if (barFocused) {
      termRef.current?.blur();
    }
  }, [barFocused]);

  useEffect(() => {
    if (!visible || isQueued || isCompleted) return;

    const attachKey = `${sessionRunId}:${lane.lane_id}:${lane.agent_type}`;
    const token = ++attachTokenRef.current;
    const alreadyAttached =
      attachedKeyRef.current === attachKey && isPtyLiveStatus(clutchStore.getLanePtyStatus(lane.lane_id));

    if (alreadyAttached) {
      setConnectPhase('ready');
      setPtyStatus(clutchStore.getLanePtyStatus(lane.lane_id) || 'ready');
      refreshLayout();
      return;
    }

    setConnectPhase('connecting');

    const attach = async () => {
      try {
        await clutchStore.connect(sessionRunId);
        if (token !== attachTokenRef.current) return;

        if (attachedKeyRef.current && attachedKeyRef.current !== attachKey) {
          await clutchStore.detachInteractivePty(lane.lane_id);
          if (token !== attachTokenRef.current) return;
          termRef.current?.reset();
        }

        await clutchStore.attachInteractivePty(lane.agent_type, lane.lane_id);
        if (token !== attachTokenRef.current) return;

        attachedKeyRef.current = attachKey;
        refreshLayout();

        if (isPtyLiveStatus(clutchStore.getLanePtyStatus(lane.lane_id))) {
          setConnectPhase('ready');
        }
      } catch {
        if (token === attachTokenRef.current) setConnectPhase('failed');
      }
    };

    void attach();
    return () => {
      attachTokenRef.current += 1;
    };
  }, [visible, lane.lane_id, lane.agent_type, sessionRunId, isQueued, isCompleted]);

  const statusDotClass =
    lane.status === 'booting'
      ? 'bg-amber-400 animate-pulse'
      : lane.status === 'running' || connectPhase === 'ready'
        ? 'bg-emerald-500'
        : lane.status === 'completed'
          ? 'bg-on-surface-variant/40'
          : lane.status === 'queued'
            ? 'bg-primary/60'
            : 'bg-on-surface-variant/30';

  return (
    <div
      ref={assignPaneRef}
      data-testid={`terminal-lane-${lane.lane_id}`}
      data-lane-id={lane.lane_id}
      className={`flex flex-col min-h-[180px] rounded-xl border overflow-hidden bg-neutral-900 ${
        lane.focused ? 'border-outline-variant ring-1 ring-primary/30' : 'border-outline-variant/50'
      }`}
      onMouseDown={() => onFocusLane(lane.lane_id)}
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b border-outline-variant/30 bg-surface-container-lowest font-mono text-[10px] text-on-surface-variant">
        {brandLogo ? (
          <img src={brandLogo} alt="" className="w-4 h-4 rounded object-contain shrink-0" />
        ) : (
          <span className={`w-2 h-2 rounded-full shrink-0 ${statusDotClass}`} />
        )}
        <span className="truncate font-semibold text-on-surface">{displayName}</span>
        <span className="truncate text-on-surface-variant/80 flex-1 min-w-0">{lane.label}</span>
        <div className="flex items-center gap-1 shrink-0 ml-auto">
          {!isCompleted && !isQueued ? (
            <button
              type="button"
              className="p-1 rounded hover:bg-surface-container-high text-on-surface-variant"
              title={t('Mark lane complete')}
              onClick={(e) => {
                e.stopPropagation();
                onCompleteLane(lane.lane_id);
              }}
            >
              <CheckCircle2 className="w-3 h-3" />
            </button>
          ) : null}
          {!isCompleted && !isQueued ? (
            <button
              type="button"
              className="p-1 rounded hover:bg-surface-container-high text-on-surface-variant"
              title={t('Collapse lane')}
              onClick={(e) => {
                e.stopPropagation();
                onCollapseLane(lane.lane_id);
              }}
            >
              <Minimize2 className="w-3 h-3" />
            </button>
          ) : null}
        </div>
      </div>
      <div className="relative flex-1 min-h-[140px]">
        {isQueued ? (
          <div className="absolute inset-0 flex items-center justify-center p-4 text-center">
            <p className="text-xs font-mono text-on-surface-variant">{t('Lane queued — max PTY lanes reached')}</p>
          </div>
        ) : isCompleted ? (
          <div className="absolute inset-0 flex items-center justify-center p-4 text-center">
            <p className="text-xs font-mono text-on-surface-variant">{t('Lane completed')}</p>
          </div>
        ) : (
          <>
            <div ref={hostRef} className="absolute inset-0 p-1" />
            {connectPhase === 'connecting' ? (
              <div className="absolute inset-0 flex items-center justify-center bg-neutral-900/80 pointer-events-none">
                <p className="text-xs font-mono text-on-surface-variant animate-pulse">{t('Connecting interactive CLI…')}</p>
              </div>
            ) : null}
            {connectPhase === 'failed' ? (
              <div className="absolute inset-0 flex items-center justify-center bg-neutral-900/90 p-4 text-center">
                <p className="text-xs font-mono text-error">{t('Interactive PTY unavailable')}</p>
              </div>
            ) : null}
          </>
        )}
        {ptyStatus && !isQueued && !isCompleted ? (
          <span className="sr-only">{ptyStatus}</span>
        ) : null}
      </div>
    </div>
  );
};
