import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { fetchWorkspaceFile } from '../../services/workspaceApi';
import { useLanguage } from '../LanguageContext';
import { BTN_ICON, BTN_GHOST_SM } from '../ui/buttonStyles';

interface HandoffPreviewModalProps {
  path: string;
  onClose: () => void;
}

type HandoffSection = {
  title: string;
  body: string;
};

function parseHandoffSections(content: string): { headline: string; sections: HandoffSection[] } {
  const trimmed = content.trim();
  if (!trimmed) return { headline: '', sections: [] };

  const lines = trimmed.split('\n');
  const headline = lines[0]?.startsWith('# ') ? lines[0].slice(2).trim() : '';
  const rest = headline ? lines.slice(1).join('\n') : trimmed;
  const chunks = rest.split(/^## /m).filter(Boolean);

  const sections = chunks.map((chunk) => {
    const nl = chunk.indexOf('\n');
    if (nl === -1) return { title: chunk.trim(), body: '' };
    return {
      title: chunk.slice(0, nl).trim(),
      body: chunk.slice(nl + 1).trim(),
    };
  });

  return { headline, sections };
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

  const parsed = useMemo(() => parseHandoffSections(content), [content]);

  return createPortal(
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 backdrop-blur-[2px] p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="handoff-preview-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl border border-outline-variant/30 bg-surface-bright shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-outline-variant/30 shrink-0">
          <div className="min-w-0">
            <h3 id="handoff-preview-title" className="text-sm font-bold text-on-surface truncate">
              {parsed.headline || path.split('/').pop()}
            </h3>
            <p className="text-[10px] font-mono text-on-surface-variant truncate mt-0.5">{path}</p>
          </div>
          <button type="button" className={BTN_ICON} onClick={onClose} aria-label={t('Close')}>
            <X className="w-4 h-4" />
          </button>
        </header>
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {loading ? (
            <p className="text-[11px] text-on-surface-variant">{t('Loading handoff')}</p>
          ) : error ? (
            <p className="text-[11px] text-error">{error}</p>
          ) : parsed.sections.length > 0 ? (
            parsed.sections.map((section) => (
              <section
                key={section.title}
                className="rounded-xl border border-outline-variant/30 bg-surface-container-low p-3"
              >
                <h4 className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2">
                  {section.title}
                </h4>
                <pre className="text-[11px] text-on-surface whitespace-pre-wrap font-mono leading-relaxed">
                  {section.body}
                </pre>
              </section>
            ))
          ) : (
            <pre className="text-[11px] text-on-surface whitespace-pre-wrap font-mono">{content}</pre>
          )}
        </div>
        <footer className="flex justify-end gap-2 px-4 py-3 border-t border-outline-variant/30 shrink-0">
          <button type="button" className={BTN_GHOST_SM} onClick={onClose}>
            {t('Close')}
          </button>
        </footer>
      </div>
    </div>,
    document.body,
  );
};
