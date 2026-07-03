import React, { useEffect } from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import { useLanguage } from './LanguageContext';

export type CliScanNoticeState = {
  tone: 'info' | 'success' | 'error';
  message: string;
} | null;

type CliScanNoticeProps = {
  notice: CliScanNoticeState;
  onDismiss: () => void;
};

export function useCliScanNotice(autoDismissMs = 5000) {
  const [notice, setNotice] = React.useState<CliScanNoticeState>(null);

  useEffect(() => {
    if (!notice || notice.tone === 'error') return undefined;
    const timer = window.setTimeout(() => setNotice(null), autoDismissMs);
    return () => window.clearTimeout(timer);
  }, [autoDismissMs, notice]);

  return { notice, setNotice, dismissNotice: () => setNotice(null) };
}

export const CliScanNotice: React.FC<CliScanNoticeProps> = ({ notice, onDismiss }) => {
  const { t } = useLanguage();
  if (!notice) return null;

  const toneClass =
    notice.tone === 'error'
      ? 'text-rose-800 bg-rose-50 border-rose-100'
      : notice.tone === 'success'
        ? 'text-emerald-800 bg-emerald-50 border-emerald-100'
        : 'text-neutral-700 bg-neutral-50 border-neutral-200';

  return (
    <div className={`flex items-start justify-between gap-2 text-xs border rounded-xl px-3 py-2 ${toneClass}`}>
      <p className="leading-relaxed">{notice.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="shrink-0 text-[10px] font-semibold uppercase tracking-wide opacity-70 hover:opacity-100"
        aria-label={t('Dismiss')}
      >
        {t('Dismiss')}
      </button>
    </div>
  );
};

export const CliScanRescanButton: React.FC<{
  loading: boolean;
  label?: string;
  onClick: () => void;
}> = ({ loading, label, onClick }) => {
  const { t } = useLanguage();
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10.5px] font-semibold border border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50 disabled:opacity-50"
    >
      <LegacyIcon name="sync" className={`text-[13px] ${loading ? 'animate-spin' : ''}`} />
      {loading ? t('Scanning…') : (label ?? t('Rescan'))}
    </button>
  );
};
