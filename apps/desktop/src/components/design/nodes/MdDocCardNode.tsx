import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { FileText, X } from 'lucide-react';
import { useLanguage } from '../../LanguageContext';

type MdDocData = {
  name: string;
  text: string;
};

function MdDocFullModal({ name, text, onClose }: { name: string; text: string; onClose: () => void }) {
  const { t } = useLanguage();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return createPortal(
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 backdrop-blur-[2px] p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="md-doc-preview-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl border border-outline-variant/30 bg-surface-bright shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-outline-variant/30 shrink-0">
          <div className="min-w-0">
            <h3 id="md-doc-preview-title" className="text-sm font-bold text-on-surface truncate">
              {name || 'DESIGN.md'}
            </h3>
            <p className="text-[10px] text-on-surface-variant truncate mt-0.5">
              {text.length.toLocaleString()} {t('characters')}
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
            onClick={onClose}
            aria-label={t('Close')}
          >
            <X size={16} />
          </button>
        </header>
        <div className="flex-1 overflow-auto p-4">
          <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-on-surface">
            {text}
          </pre>
        </div>
        <footer className="flex justify-end gap-2 px-4 py-3 border-t border-outline-variant/30 shrink-0">
          <button
            type="button"
            className="rounded-lg px-3 py-1.5 text-[11px] font-medium text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
            onClick={onClose}
          >
            {t('Close')}
          </button>
        </footer>
      </div>
    </div>,
    document.body,
  );
}

export function MdDocCardNode({ data }: NodeProps) {
  const d = data as MdDocData;
  const [showFull, setShowFull] = useState(false);
  return (
    <>
      <div className="w-[300px] overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-md animate-design-card-in">
        <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
        <div className="flex items-center justify-between gap-2 border-b border-neutral-100 px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <FileText size={14} className="shrink-0 text-neutral-500" />
            <p className="truncate text-[12px] font-semibold text-neutral-800">{d.name || 'DESIGN.md'}</p>
          </div>
          <button
            type="button"
            className="nodrag nopan shrink-0 rounded-md border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-neutral-600 hover:bg-neutral-100 hover:text-neutral-800"
            onClick={(e) => { e.stopPropagation(); setShowFull(true); }}
          >
            View full
          </button>
        </div>
        <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap bg-neutral-50/80 px-3 py-2.5 font-mono text-[10px] leading-relaxed text-neutral-600">
          {d.text.slice(0, 3500)}
          {d.text.length > 3500 ? '\n…(truncated — click "View full" to see all)' : ''}
        </pre>
      </div>
      {showFull && <MdDocFullModal name={d.name} text={d.text} onClose={() => setShowFull(false)} />}
    </>
  );
}
