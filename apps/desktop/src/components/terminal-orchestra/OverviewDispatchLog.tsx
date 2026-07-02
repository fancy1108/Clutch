import React, { useState } from 'react';
import type { DispatchLogEntry } from '../../types';
import { useLanguage } from '../LanguageContext';
import { HandoffPreviewModal } from './HandoffPreviewModal';

interface OverviewDispatchLogProps {
  entries: DispatchLogEntry[];
}

export const OverviewDispatchLog: React.FC<OverviewDispatchLogProps> = ({ entries }) => {
  const { t } = useLanguage();
  const [previewPath, setPreviewPath] = useState<string | null>(null);

  if (entries.length === 0) {
    return (
      <p className="text-[11px] text-on-surface-variant text-center py-4 border border-dashed border-outline-variant/40 rounded-xl">
        {t('No dispatch records yet')}
      </p>
    );
  }

  return (
    <>
      <ul data-testid="overview-dispatch-log" className="space-y-2">
        {entries.map((entry) => (
          <li
            key={entry.id}
            className="rounded-xl border border-outline-variant/40 bg-surface-container-low p-2.5"
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-[9px] font-mono text-on-surface-variant">{entry.time}</span>
              <span className="text-[9px] uppercase tracking-wider text-on-surface-variant/70">
                {entry.input_mode === 'graph' ? t('Graph') : t('Natural')}
              </span>
            </div>
            <p className="text-[10px] font-semibold text-on-surface mb-1">
              {entry.sources_label} → {entry.target}
            </p>
            <p className="text-[10px] text-on-surface-variant line-clamp-2 mb-2">{entry.prompt}</p>
            <p className="text-[9px] font-mono text-on-surface-variant/80 truncate mb-2">
              {entry.handoff_path}
            </p>
            <div className="flex gap-1.5">
              <button
                type="button"
                className="flex-1 text-[9px] font-semibold px-2 py-1 rounded-lg border border-outline-variant/40 bg-surface-bright hover:bg-surface-container-high"
                onClick={() => setPreviewPath(entry.handoff_path)}
              >
                {t('Preview handoff')}
              </button>
              <button
                type="button"
                className="flex-1 text-[9px] font-semibold px-2 py-1 rounded-lg border border-outline-variant/40 bg-surface-bright hover:bg-surface-container-high"
                onClick={() => {
                  window.dispatchEvent(
                    new CustomEvent('orchestrator-fill-bar', {
                      detail: { text: entry.prompt },
                    }),
                  );
                }}
              >
                {t('Send to Bar')}
              </button>
            </div>
          </li>
        ))}
      </ul>
      {previewPath ? (
        <HandoffPreviewModal path={previewPath} onClose={() => setPreviewPath(null)} />
      ) : null}
    </>
  );
};
