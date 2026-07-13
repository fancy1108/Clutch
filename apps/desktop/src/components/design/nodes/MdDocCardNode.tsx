import React, { useState } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { FileText, X } from 'lucide-react';

type MdDocData = {
  name: string;
  text: string;
};

function MdDocFullModal({ name, text, onClose }: { name: string; text: string; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative mx-4 flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-neutral-100 px-4 py-3">
          <div className="flex items-center gap-2">
            <FileText size={14} className="shrink-0 text-neutral-500" />
            <p className="text-[13px] font-semibold text-neutral-800">{name || 'DESIGN.md'}</p>
            <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] text-neutral-500">{text.length.toLocaleString()} chars</span>
          </div>
          <button
            type="button"
            className="rounded-lg p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
        <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap bg-neutral-50 px-4 py-3 font-mono text-[11px] leading-relaxed text-neutral-700">
          {text}
        </pre>
      </div>
    </div>
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
