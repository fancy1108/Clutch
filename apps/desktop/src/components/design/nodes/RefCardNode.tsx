import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { ImagePlus } from 'lucide-react';

type RefData = {
  name: string;
  url: string;
};

export function RefCardNode({ data }: NodeProps) {
  const d = data as RefData;
  return (
    <div className="w-[300px] overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-md animate-design-card-in">
      <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
      <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
      <div className="flex items-center justify-between border-b border-neutral-100 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <ImagePlus size={14} className="shrink-0 text-amber-500" />
          <p className="truncate text-[12px] font-semibold text-neutral-800">{d.name || 'image.png'}</p>
        </div>
        <span className="shrink-0 text-[10px] text-neutral-400">Reference</span>
      </div>
      <img src={d.url} alt={d.name} className="max-h-[280px] w-full object-contain bg-neutral-50" />
    </div>
  );
}
