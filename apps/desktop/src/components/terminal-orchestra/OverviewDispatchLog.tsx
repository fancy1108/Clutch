import React, { useEffect, useState } from 'react';
import { ArrowRight, FileText, Loader2, Send } from 'lucide-react';
import type { DispatchLogEntry } from '../../types';
import {
  isHandoffDispatchEntry,
  buildHandoffSendToBarTextFromEntry,
  isDispatchEntryTargetPending,
  findLaneForDispatchTarget,
} from '../../services/terminalOrchestraUtils';
import { clutchStore, useClutchState } from '../../services/clutchState';
import { useLanguage } from '../LanguageContext';
import { formatDispatchTime } from '../../services/formatTime';
import { BTN_PRIMARY_SM, BTN_SECONDARY_SM } from '../ui/buttonStyles';
import { HandoffPreviewModal } from './HandoffPreviewModal';

interface OverviewDispatchLogProps {
  entries: DispatchLogEntry[];
  readOnly?: boolean;
  onSelectEntry?: (entryId: string) => void;
}

const OVERVIEW_CARD =
  'rounded-2xl border border-outline-variant/30 bg-surface-container-low shadow-sm';

export const OverviewDispatchLog: React.FC<OverviewDispatchLogProps> = ({
  entries,
  readOnly = false,
  onSelectEntry,
}) => {
  const { t } = useLanguage();
  const { state: clutchState } = useClutchState();
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const lanes = clutchState.pty_lanes ?? [];
  const pendingInject = clutchState.pending_pty_inject;
  const [, setPtyTick] = useState(0);

  useEffect(() => {
    const laneIds = new Set<string>();
    for (const entry of entries) {
      const lane = findLaneForDispatchTarget(lanes, entry.target, entry.lane_sessions);
      if (lane) laneIds.add(lane.lane_id);
    }
    const unsubs = [...laneIds].map((laneId) =>
      clutchStore.onPtyStatusChangeForLane(laneId, () => {
        setPtyTick((n) => n + 1);
      }),
    );
    const globalUnsub = clutchStore.onPtyStatusChange(() => {
      setPtyTick((n) => n + 1);
    });
    return () => {
      unsubs.forEach((unsub) => unsub());
      globalUnsub();
    };
  }, [entries, lanes]);

  if (entries.length === 0) {
    return (
      <p className="text-[11px] text-on-surface-variant text-center py-6 border border-dashed border-outline-variant/40 rounded-2xl">
        {t('No dispatch records yet')}
      </p>
    );
  }

  return (
    <>
      <ul data-testid="overview-dispatch-log" className="space-y-2.5">
        {entries.map((entry) => {
          const showHandoff = isHandoffDispatchEntry(entry);
          const targetPending = isDispatchEntryTargetPending(
            entry,
            lanes,
            pendingInject,
            (laneId) => clutchStore.getLanePtyStatus(laneId),
          );
          return (
            <li
              key={entry.id}
              className={`${OVERVIEW_CARD} p-3 transition-colors ${
                onSelectEntry ? 'cursor-pointer hover:bg-surface-container-high' : ''
              } ${targetPending ? 'ring-1 ring-primary/25' : ''}`}
              onClick={() => onSelectEntry?.(entry.id)}
            >
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-[10px] font-mono text-on-surface-variant">
                  {formatDispatchTime(entry.time)}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  {targetPending ? (
                    <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-primary px-1.5 py-0.5 rounded-md bg-primary/10 border border-primary/20">
                      <Loader2 className="w-3 h-3 animate-spin shrink-0" strokeWidth={2.25} />
                      {t('Opening terminal…')}
                    </span>
                  ) : null}
                  <span className="text-[9px] uppercase tracking-wider font-bold text-on-surface-variant/70 px-1.5 py-0.5 rounded-md bg-surface-container-high border border-outline-variant/30">
                    {entry.input_mode === 'graph' ? t('Graph') : t('Natural')}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1.5 mb-1.5 min-w-0">
                <span className="text-[11px] font-semibold text-on-surface truncate">
                  {entry.sources_label}
                </span>
                <ArrowRight className="w-3 h-3 shrink-0 text-on-surface-variant/60" strokeWidth={2.25} />
                <span
                  className={`text-[11px] font-semibold truncate ${
                    targetPending ? 'text-primary' : 'text-on-surface'
                  }`}
                >
                  {entry.target}
                </span>
              </div>
              <p className="text-[11px] text-on-surface-variant leading-relaxed line-clamp-2 mb-2">
                {entry.prompt}
              </p>
              {showHandoff ? (
                <>
                  <p className="text-[9px] font-mono text-on-surface-variant/80 truncate mb-2.5 px-2 py-1 rounded-lg bg-white border border-outline-variant/30">
                    {entry.handoff_file || entry.handoff_path}
                  </p>
                  <div className="flex gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className={`${BTN_SECONDARY_SM} flex-1 gap-1`}
                      onClick={() => setPreviewPath(entry.handoff_path)}
                    >
                      <FileText className="w-3 h-3 shrink-0" strokeWidth={2.25} />
                      {t('Preview handoff')}
                    </button>
                    {!readOnly ? (
                      <button
                        type="button"
                        className={`${BTN_PRIMARY_SM} flex-1 gap-1`}
                        onClick={() => {
                          window.dispatchEvent(
                            new CustomEvent('orchestrator-fill-bar', {
                              detail: { text: buildHandoffSendToBarTextFromEntry(entry) },
                            }),
                          );
                        }}
                      >
                        <Send className="w-3 h-3 shrink-0" strokeWidth={2.25} />
                        {t('Send to Bar')}
                      </button>
                    ) : null}
                  </div>
                </>
              ) : null}
            </li>
          );
        })}
      </ul>
      {previewPath ? (
        <HandoffPreviewModal path={previewPath} onClose={() => setPreviewPath(null)} />
      ) : null}
    </>
  );
};
