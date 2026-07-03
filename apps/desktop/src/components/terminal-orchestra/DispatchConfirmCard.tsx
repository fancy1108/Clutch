import React from 'react';
import type { DispatchPreviewPayload } from '../../types';
import { useLanguage } from '../LanguageContext';
import { BTN_PRIMARY, BTN_SECONDARY } from '../ui/buttonStyles';

interface DispatchConfirmCardProps {
  preview: DispatchPreviewPayload;
  activeChips: string[];
  onToggleChip: (sourceName: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
}

export const DispatchConfirmCard: React.FC<DispatchConfirmCardProps> = ({
  preview,
  activeChips,
  onToggleChip,
  onCancel,
  onConfirm,
}) => {
  const { t } = useLanguage();
  const sourcesLabel = activeChips.length > 0 ? activeChips.join(' + ') : t('Workspace source');

  return (
    <div
      data-testid="dispatch-confirm-card"
      className="absolute left-0 right-0 bottom-full mb-2 z-50 max-h-[min(42vh,300px)] overflow-y-auto rounded-xl border border-outline-variant bg-surface-bright shadow-lg p-3.5"
    >
      <h3 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-2">
        {t('Confirm dispatch')}
      </h3>
      <p className="text-[10px] text-on-surface-variant/80 mb-2">
        {t('Confirm card hint')}
      </p>
      <span
        className={`inline-block text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md mb-2 ${
          preview.input_mode === 'graph'
            ? 'bg-primary/10 text-primary'
            : 'bg-surface-container-low text-on-surface-variant'
        }`}
      >
        {preview.input_mode === 'graph' ? t('Graph syntax') : t('Natural language')}
      </span>
      <div className="flex items-center flex-wrap gap-2 p-2.5 rounded-lg border border-outline-variant/40 bg-surface-container-low mb-2 text-xs">
        <span className="font-bold px-2 py-1 rounded-lg border border-outline-variant/40 bg-surface-bright">
          @{sourcesLabel}
        </span>
        <span className="text-on-surface-variant font-bold">→</span>
        <span className="font-bold px-2 py-1 rounded-lg bg-neutral-900 text-white">
          @{preview.target}
        </span>
      </div>
      {preview.task ? (
        <p className="text-[11px] text-on-surface-variant mb-2 leading-relaxed">{preview.task}</p>
      ) : null}
      {preview.file_refs?.length ? (
        <div className="flex flex-wrap gap-1 mb-2">
          {preview.file_refs.map((ref) => (
            <span
              key={ref}
              className="text-[9px] font-mono px-2 py-0.5 rounded-md border border-outline-variant/40 bg-surface-container-low"
            >
              @{ref}
            </span>
          ))}
        </div>
      ) : null}
      {preview.chips?.length ? (
        <details className="mb-2 text-[10px]">
          <summary className="cursor-pointer text-on-surface-variant font-semibold mb-1">
            {t('Adjust handoff sources')}
          </summary>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {preview.chips.map((chip) => {
              const on = activeChips.includes(chip.source_name);
              return (
                <button
                  key={chip.id}
                  type="button"
                  onClick={() => onToggleChip(chip.source_name)}
                  className={`text-[9px] font-semibold px-2 py-1 rounded-lg border transition-colors ${
                    on
                      ? 'bg-neutral-900 text-white border-neutral-900'
                      : 'bg-surface-container-low text-on-surface-variant border-outline-variant/40'
                  }`}
                >
                  {chip.label}
                </button>
              );
            })}
          </div>
        </details>
      ) : null}
      <p className="text-[10px] text-on-surface-variant mb-1">{t('Will generate handoff file')}</p>
      <p className="text-[10px] font-mono text-on-surface mb-3 truncate">{preview.handoff_path}</p>
      <div className="flex gap-2 justify-end">
        <button type="button" className={BTN_SECONDARY} onClick={onCancel}>
          {t('Cancel')}
        </button>
        <button type="button" className={BTN_PRIMARY} onClick={onConfirm} data-testid="confirm-dispatch-btn">
          {t('Confirm dispatch')}
        </button>
      </div>
    </div>
  );
};
