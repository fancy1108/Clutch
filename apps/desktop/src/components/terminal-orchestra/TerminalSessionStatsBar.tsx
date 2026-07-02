import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { clutchStore, useClutchState } from '../../services/clutchState';
import { useLanguage } from '../LanguageContext';
import { BTN_GHOST_SM } from '../ui/buttonStyles';

interface TerminalSessionStatsBarProps {
  sessionRunId: string;
  visible: boolean;
}

export const TerminalSessionStatsBar: React.FC<TerminalSessionStatsBarProps> = ({
  sessionRunId,
  visible,
}) => {
  const { t } = useLanguage();
  const { state } = useClutchState();
  const [liveTotal, setLiveTotal] = useState(0);
  const [busy, setBusy] = useState(false);

  const visibleLaneIds = useMemo(() => {
    const lanes = state.pty_lanes ?? [];
    const effective =
      lanes.length > 0
        ? lanes
        : [{ lane_id: 'lane_primary', status: 'running' as const }];
    return effective
      .filter((lane) => lane.status !== 'completed' && lane.status !== 'queued')
      .map((lane) => lane.lane_id);
  }, [state.pty_lanes]);

  const refresh = useCallback(async () => {
    if (!visible) return;
    try {
      const stats = await clutchStore.fetchPtySessionStats();
      setLiveTotal(stats.total);
    } catch {
      setLiveTotal(0);
    }
  }, [visible]);

  useEffect(() => {
    void refresh();
    const unsubClosed = clutchStore.onPtySessionsClosed(() => {
      void refresh();
    });
    const interval = window.setInterval(() => {
      void refresh();
    }, 8000);
    return () => {
      unsubClosed();
      window.clearInterval(interval);
    };
  }, [refresh, sessionRunId, visibleLaneIds.join(',')]);

  const backgroundCount = Math.max(0, liveTotal - visibleLaneIds.length);
  const canCloseOthers = backgroundCount > 0 && visibleLaneIds.length > 0;

  const handleCloseOthers = async () => {
    if (busy || !canCloseOthers) return;
    setBusy(true);
    try {
      await clutchStore.closeOtherPtySessions(visibleLaneIds);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  if (!visible) return null;

  const summaryParts = t('Background terminals: {count} total').split('{count}');

  return (
    <div
      data-testid="terminal-session-stats-bar"
      className="flex items-center justify-between gap-3 w-full min-h-[26px] px-3 py-1 rounded-xl border border-outline-variant/30 bg-surface-container-low/40 shadow-sm"
    >
      <p className="min-w-0 truncate text-[10px] leading-snug text-on-surface-variant font-mono">
        {summaryParts[0]}
        <span className="tabular-nums text-on-surface">{liveTotal}</span>
        {summaryParts[1] ?? ''}
      </p>
      <button
        type="button"
        data-testid="terminal-close-others-btn"
        disabled={busy || !canCloseOthers}
        onClick={() => void handleCloseOthers()}
        className={`${BTN_GHOST_SM} shrink-0 !px-2 !py-0.5 text-[10px] normal-case tracking-normal`}
      >
        {t('Close other terminals')}
      </button>
    </div>
  );
};
