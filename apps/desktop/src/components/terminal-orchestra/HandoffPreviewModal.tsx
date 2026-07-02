import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { fetchWorkspaceFile } from '../../services/workspaceApi';
import { useLanguage } from '../LanguageContext';
import { BTN_SECONDARY } from '../ui/buttonStyles';

interface HandoffPreviewModalProps {
  path: string;
  onClose: () => void;
}

export const HandoffPreviewModal: React.FC<HandoffPreviewModalProps> = ({ path, onClose }) => {
  const { t } = useLanguage();
  const [content, setContent] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void fetchWorkspaceFile(path)
      .then((text) => {
        if (!cancelled) {
          setContent(text);
          setError('');
        }
      })
      .catch(() => {
        if (!cancelled) setError(t('Failed to load handoff file'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, t]);

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-neutral-900/40 p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="handoff-preview-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl border border-outline-variant bg-surface-bright shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-outline-variant/30">
          <h3 id="handoff-preview-title" className="text-sm font-bold text-on-surface truncate font-mono">
            {path.split('/').pop()}
          </h3>
          <button type="button" className={BTN_SECONDARY} onClick={onClose} aria-label={t('Close')}>
            <X className="w-4 h-4" />
          </button>
        </header>
        <div className="flex-1 overflow-auto p-4 font-mono text-[11px] text-on-surface whitespace-pre-wrap">
          {loading ? (
            <p className="text-on-surface-variant">{t('Loading handoff')}</p>
          ) : error ? (
            <p className="text-error">{error}</p>
          ) : (
            content
          )}
        </div>
      </div>
    </div>
  );
};
