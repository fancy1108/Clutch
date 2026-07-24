import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { Minimize2 } from 'lucide-react';
import { useLanguage } from '../LanguageContext';
import type { PtyLane } from '../../types';
import { clutchStore, useClutchState } from '../../services/clutchState';
import { resolveBrandLogoSrc } from '../../services/brandLogos';
import {
  laneHeaderAgentName,
  laneShellBorderClass,
  LANE_SHELL_CLASS,
  resolvePtyInjectWarmupMs,
  waitForPtyOutputReadyForInject,
  type LaneGridLayout,
} from '../../services/terminalOrchestraUtils';
import { scheduleXtermRefit, wakeXtermTerminal } from './terminalLaneLayout';
import { createWorkspacePathLinkProvider } from './terminalPathLinkProvider';

interface TerminalLanePaneProps {
  lane: PtyLane;
  sessionRunId: string;
  /** Terminal workspace mode is active (chat vs terminal toggle). */
  workspaceVisible: boolean;
  /** Lane is in a visible grid slot (not collapsed, paginated away, or off-screen keep-alive). */
  gridVisible: boolean;
  barFocused: boolean;
  configuredAgents: Array<{ name: string; agentType?: string }>;
  headerAgentName?: string;
  /** Distinguish preview agents that share the same CLI tool (e.g. Opencode vs Opencode2). */
  attachIdentity?: string;
  onFocusLane: (laneId: string) => void;
  onCollapseLane: (laneId: string) => void;
  paneRef?: (el: HTMLDivElement | null, laneId: string) => void;
  /** Bumped when grid resizes or lane count changes — triggers xterm refit. */
  layoutTick?: number;
  layoutMode?: LaneGridLayout;
  /** Click workspace path/filename in xterm → App file preview. */
  onOpenWorkspaceFile?: (path: string) => void;
}

function isPtyLiveStatus(status: string): boolean {
  return status === 'ready' || status === 'booting';
}

export const TerminalLanePane: React.FC<TerminalLanePaneProps> = ({
  lane,
  sessionRunId,
  workspaceVisible,
  gridVisible,
  barFocused,
  configuredAgents,
  headerAgentName,
  attachIdentity,
  onFocusLane,
  onCollapseLane,
  paneRef,
  layoutTick = 0,
  layoutMode = 'single',
  onOpenWorkspaceFile,
}) => {
  const onOpenWorkspaceFileRef = useRef(onOpenWorkspaceFile);
  onOpenWorkspaceFileRef.current = onOpenWorkspaceFile;
  const { t } = useLanguage();
  const hostRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const attachTokenRef = useRef(0);
  const attachedKeyRef = useRef<string | null>(null);
  const consumedInjectRef = useRef<string | null>(null);
  const injectInflightRef = useRef<string | null>(null);
  const [ptyStatus, setPtyStatus] = useState('');
  const [ptyErrorDetail, setPtyErrorDetail] = useState('');
  const [connectPhase, setConnectPhase] = useState<'idle' | 'connecting' | 'ready' | 'failed'>('idle');
  const { state: clutchState } = useClutchState();
  const pendingInject = clutchState.pending_pty_inject;

  const displayName = headerAgentName ?? laneHeaderAgentName(lane, configuredAgents);
  const brandLogo = resolveBrandLogoSrc({ agentType: lane.agent_type });
  const isQueued = lane.status === 'queued';
  const isCompleted = lane.status === 'completed';

  const assignPaneRef = useCallback(
    (el: HTMLDivElement | null) => {
      paneRef?.(el, lane.lane_id);
    },
    [paneRef, lane.lane_id],
  );

  const barFocusedRef = useRef(barFocused);
  barFocusedRef.current = barFocused;

  const workspaceVisibleRef = useRef(workspaceVisible);
  workspaceVisibleRef.current = workspaceVisible;

  const gridVisibleRef = useRef(gridVisible);
  gridVisibleRef.current = gridVisible;

  const refreshLayout = useCallback(() => {
    const host = hostRef.current;
    const term = termRef.current;
    const fitAddon = fitRef.current;
    if (!host || !term || !fitAddon) return;
    if (!wakeXtermTerminal(term, fitAddon, host)) return;
    void clutchStore.sendPtyResize(term.cols, term.rows, lane.lane_id);
    if (!barFocusedRef.current && gridVisibleRef.current) term.focus();
  }, [lane.lane_id]);

  const refreshLayoutRef = useRef(refreshLayout);
  refreshLayoutRef.current = refreshLayout;

  const [isInjectPending, setInjectPending] = useState(false);
  const flushPendingInject = useCallback(async () => {
    if (isQueued || isCompleted) return;

    const pending = clutchStore.getSnapshot().pending_pty_inject;
    // If this lane has a pending inject, show loading overlay
    if (pending && pending.lane_id === lane.lane_id) {
      setInjectPending(true);
    }
    if (!pending || pending.lane_id !== lane.lane_id) return;

    if (pending.handoff_path) {
      const dispatchLog = clutchStore.getSnapshot().dispatch_log ?? [];
      const entry = dispatchLog.find((e) => e.handoff_path === pending.handoff_path);
      if (entry && entry.step_status === 'generating_handoff') {
        return;
      }
    }

    const dedupeKey = `${pending.lane_id}:${pending.prompt}:${pending.handoff_path ?? ''}`;
    if (consumedInjectRef.current === dedupeKey || injectInflightRef.current === dedupeKey) return;

    injectInflightRef.current = dedupeKey;
    try {
      for (let attempt = 0; attempt < 32; attempt += 1) {
        if (clutchStore.getLanePtyStatus(lane.lane_id) !== 'ready') {
          await new Promise((resolve) => window.setTimeout(resolve, 250));
          continue;
        }
        await waitForPtyOutputReadyForInject(
          lane.lane_id,
          lane.agent_type,
          (laneId) => clutchStore.getLaneTranscript(laneId),
        );
        const isHandoff = Boolean(pending.handoff_path?.trim());
        const warmupMs = resolvePtyInjectWarmupMs(lane.agent_type, { isHandoff, attempt });
        const ok = await clutchStore.submitPtyPrompt(lane.lane_id, pending.prompt, { warmupMs });
        if (ok) {
          consumedInjectRef.current = dedupeKey;
          setInjectPending(false);
          await clutchStore.ackPendingPtyInject();
          refreshLayout();
          return;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 600));
      }
    } finally {
      if (injectInflightRef.current === dedupeKey) {
        setInjectPending(false);

        injectInflightRef.current = null;
      }
    }
  }, [isCompleted, isQueued, lane.agent_type, lane.lane_id, refreshLayout]);

  useEffect(() => {
    if (isQueued || isCompleted) return;
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
    const linkDisposable = term.registerLinkProvider(
      createWorkspacePathLinkProvider(term, (path) => {
        onOpenWorkspaceFileRef.current?.(path);
      }),
    );
    term.open(host);
    try {
      fitAddon.fit();
    } catch {
      // Host may not have dimensions yet; ResizeObserver will refit.
    }
    termRef.current = term;
    fitRef.current = fitAddon;

    const buffered = clutchStore.getLaneTranscript(lane.lane_id);
    if (buffered) {
      term.write(buffered);
    }

    const syncConnectPhaseFromStore = () => {
      const status = clutchStore.getLanePtyStatus(lane.lane_id);
      const detail = clutchStore.getLanePtyDetail(lane.lane_id);
      setPtyStatus(status);
      if (status === 'ready') {
        setConnectPhase('ready');
        setPtyErrorDetail('');
      } else if (status === 'blocked' || status === 'exited') {
        setConnectPhase('failed');
        setPtyErrorDetail(detail);
      }
    };
    syncConnectPhaseFromStore();
    window.requestAnimationFrame(() => refreshLayoutRef.current());

    const resizeObserver = new ResizeObserver(() => {
      if (!workspaceVisibleRef.current) return;
      if (host.clientWidth < 24 || host.clientHeight < 24) return;
      window.requestAnimationFrame(() => refreshLayoutRef.current());
    });
    resizeObserver.observe(host);

    const intersectionObserver = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        window.requestAnimationFrame(() => refreshLayoutRef.current());
      },
      { threshold: 0.01 },
    );
    intersectionObserver.observe(host);

    const unsubOutput = clutchStore.onPtyOutputForLane(lane.lane_id, (chunk) => {
      term.write(chunk);
      if (gridVisibleRef.current) {
        setConnectPhase((phase) => (phase === 'connecting' ? 'ready' : phase));
      }
    });
    const unsubStatus = clutchStore.onPtyStatusChangeForLane(lane.lane_id, (status) => {
      setPtyStatus(status);
      if (status === 'ready') {
        if (workspaceVisibleRef.current) {
          setConnectPhase('ready');
          setPtyErrorDetail('');
          if (gridVisibleRef.current) refreshLayoutRef.current();
        }
      } else if (status === 'blocked' || status === 'exited') {
        setConnectPhase('failed');
        setPtyErrorDetail(clutchStore.getLanePtyDetail(lane.lane_id));
      }
    });

    term.onData((data) => {
      if (gridVisibleRef.current && !barFocusedRef.current) {
        void clutchStore.sendPtyInput(data, lane.lane_id);
      }
    });

    return () => {
      unsubOutput();
      unsubStatus();
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      linkDisposable.dispose();
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, [lane.lane_id, isQueued, isCompleted]);

  useEffect(() => {
    return () => {
      attachTokenRef.current += 1;
      attachedKeyRef.current = null;
    };
  }, [lane.lane_id, sessionRunId]);

  useEffect(() => {
    if (barFocused) {
      termRef.current?.blur();
    }
  }, [barFocused]);

  useEffect(() => {
    consumedInjectRef.current = null;
    injectInflightRef.current = null;
  }, [lane.agent_type, lane.lane_id, lane.status, lane.configured_agent_id, pendingInject?.prompt, pendingInject?.lane_id, pendingInject?.handoff_path]);

  useEffect(() => {
    if (isQueued || isCompleted) return;
    if (!pendingInject || pendingInject.lane_id !== lane.lane_id) return;
    if (clutchStore.getLanePtyStatus(lane.lane_id) !== 'ready') return;
    void flushPendingInject();
  }, [
    isQueued,
    isCompleted,
    pendingInject,
    lane.lane_id,
    ptyStatus,
    connectPhase,
    flushPendingInject,
  ]);

  useEffect(() => {
    if (isQueued || isCompleted) return;
    if (!pendingInject || pendingInject.lane_id !== lane.lane_id) return;
    return clutchStore.onPtyOutputForLane(lane.lane_id, () => {
      if (clutchStore.getLanePtyStatus(lane.lane_id) !== 'ready') return;
      void flushPendingInject();
    });
  }, [isQueued, isCompleted, pendingInject, lane.lane_id, flushPendingInject]);

  useEffect(() => {
    if (!workspaceVisible || !gridVisible || isQueued || isCompleted) return;
    const status = clutchStore.getLanePtyStatus(lane.lane_id);
    if (status === 'ready') {
      setConnectPhase('ready');
      setPtyErrorDetail('');
    } else if (status === 'blocked' || status === 'exited') {
      setConnectPhase('failed');
      setPtyErrorDetail(clutchStore.getLanePtyDetail(lane.lane_id));
    }
    return scheduleXtermRefit(refreshLayout);
  }, [
    workspaceVisible,
    gridVisible,
    lane.collapsed,
    isQueued,
    isCompleted,
    layoutTick,
    layoutMode,
    lane.lane_id,
    refreshLayout,
  ]);

  useEffect(() => {
    if (!workspaceVisible || isQueued || isCompleted) {
      setConnectPhase('idle');
      return;
    }

    const attachKey = `${sessionRunId}:${lane.lane_id}:${lane.agent_type}:${attachIdentity ?? lane.lane_id}`;
    const token = ++attachTokenRef.current;
    const liveOnEnter = clutchStore.getLanePtyStatus(lane.lane_id);
    if (attachedKeyRef.current === attachKey && liveOnEnter === 'ready') {
      setConnectPhase('ready');
      setPtyErrorDetail('');
      if (gridVisibleRef.current) refreshLayoutRef.current();
      return () => {
        attachTokenRef.current += 1;
      };
    }
    setConnectPhase('connecting');

    const attach = async () => {
      try {
        await clutchStore.connect(sessionRunId);
        if (token !== attachTokenRef.current) return;

        const liveStatus = clutchStore.getLanePtyStatus(lane.lane_id);
        if (
          attachedKeyRef.current === attachKey
          && (liveStatus === 'ready' || liveStatus === 'booting')
        ) {
          if (liveStatus === 'ready') {
            setConnectPhase('ready');
            refreshLayoutRef.current();
          }
          return;
        }

        if (attachedKeyRef.current !== attachKey) {
          const live = clutchStore.getLanePtyStatus(lane.lane_id);
          if (live && live !== 'detached') {
            await clutchStore.detachInteractivePty(lane.lane_id);
            if (token !== attachTokenRef.current) return;
          }
          termRef.current?.reset();
          attachedKeyRef.current = null;
        }

        await clutchStore.attachInteractivePty(lane.agent_type, lane.lane_id, {
          configuredAgentId: lane.configured_agent_id ?? attachIdentity,
        });
        if (token !== attachTokenRef.current) return;

        attachedKeyRef.current = attachKey;
        const ready = await clutchStore.waitForLanePtyReady(lane.lane_id, 20_000);
        if (token !== attachTokenRef.current) return;

        if (ready) {
          setConnectPhase('ready');
          setPtyErrorDetail('');
          setPtyStatus(clutchStore.getLanePtyStatus(lane.lane_id) || 'ready');
          refreshLayoutRef.current();
        } else {
          setConnectPhase('failed');
          setPtyErrorDetail(clutchStore.getLanePtyDetail(lane.lane_id));
        }
      } catch (err) {
        if (token === attachTokenRef.current) {
          setConnectPhase('failed');
          setPtyErrorDetail(err instanceof Error ? err.message : String(err));
        }
      }
    };

    void attach();
    return () => {
      attachTokenRef.current += 1;
    };
  }, [workspaceVisible, lane.lane_id, lane.agent_type, lane.status, sessionRunId, attachIdentity, isQueued, isCompleted]);

  const isCollapsed = lane.collapsed;

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
      data-lane-collapsed={isCollapsed ? 'true' : 'false'}
      className={`flex flex-col h-full min-h-0 overflow-hidden ${LANE_SHELL_CLASS} ${laneShellBorderClass(lane.focused)} ${
        isCollapsed ? 'pointer-events-none' : ''
      }`}
      onMouseDown={() => {
        if (!isCollapsed) onFocusLane(lane.lane_id);
      }}
    >
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-neutral-800 bg-[#111111] font-mono text-[10px] text-neutral-500 shrink-0">
        {brandLogo ? (
          <img src={brandLogo} alt="" className="w-4 h-4 rounded object-contain shrink-0" />
        ) : (
          <span className={`w-2 h-2 rounded-full shrink-0 ${statusDotClass}`} />
        )}
        <span className="truncate font-semibold text-neutral-200 flex-1 min-w-0">{displayName}</span>
        <div className="flex items-center gap-1 shrink-0 ml-auto">
          {!isCompleted && !isQueued ? (
            <button
              type="button"
              className="p-1 rounded hover:bg-neutral-800 text-neutral-400 hover:text-neutral-200"
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
      <div className="relative flex-1 min-h-0 bg-[#111111]">
        {isQueued ? (
          <div className="absolute inset-0 flex items-center justify-center p-4 text-center bg-[#111111]">
            <p className="text-xs font-mono text-neutral-500">{t('Lane queued — max PTY lanes reached')}</p>
          </div>
        ) : isCompleted ? (
          <div className="absolute inset-0 flex items-center justify-center p-4 text-center bg-[#111111]">
            <p className="text-xs font-mono text-neutral-500">{t('Lane completed')}</p>
          </div>
        ) : (
          <>
            <div ref={hostRef} className="terminal-xterm-host absolute inset-0 p-1 bg-[#111111]" />
            {connectPhase === 'connecting' && gridVisible ? (
              <div className="absolute inset-0 flex items-center justify-center bg-[#111111]/90 pointer-events-none">
                <p className="text-xs font-mono text-neutral-500 animate-pulse">{t('Connecting interactive CLI…')}</p>
              </div>
            ) : null}
            {connectPhase === 'failed' && gridVisible ? (
              <div className="absolute inset-0 flex items-center justify-center bg-[#111111] p-4 text-center">
                <div className="space-y-1">
                  <p className="text-xs font-mono text-rose-400">{t('Interactive PTY unavailable')}</p>
                  {ptyErrorDetail ? (
                    <p className="text-[10px] font-mono text-rose-400/80 break-words max-w-md">{ptyErrorDetail}</p>
                  ) : null}
                </div>
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
