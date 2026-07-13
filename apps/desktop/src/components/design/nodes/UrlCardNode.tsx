import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Globe } from 'lucide-react';
import { hostFromUrl } from '../designWorkspaceUtils';

type UrlCardData = {
  url: string;
  host?: string;
  title?: string;
  description?: string;
};

export function UrlCardNode({ data }: NodeProps) {
  const d = data as UrlCardData;
  const host = d.host || hostFromUrl(d.url);
  return (
    <div className="w-[300px] overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-md animate-design-card-in">
      <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
      <div className="flex items-center gap-2 border-b border-neutral-100 px-3 py-2">
        <Globe size={14} className="shrink-0 text-sky-600" />
        <p className="truncate text-[12px] font-semibold text-neutral-800">{host}</p>
      </div>
      <div className="space-y-2 bg-gradient-to-br from-sky-50/80 to-white px-3 py-3">
        <p className="text-[13px] font-semibold leading-snug text-neutral-900">
          {d.title || host}
        </p>
        {d.description ? (
          <p className="line-clamp-4 text-[11px] leading-relaxed text-neutral-500">{d.description}</p>
        ) : (
          <p className="text-[11px] text-neutral-400">Website reference</p>
        )}
        <a
          href={d.url.startsWith('http') ? d.url : `https://${d.url}`}
          target="_blank"
          rel="noreferrer"
          className="block truncate text-[10px] text-sky-600 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {d.url}
        </a>
      </div>
    </div>
  );
}
