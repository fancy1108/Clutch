import React from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Loader2 } from 'lucide-react';
import type { SpecData } from '../designWorkspaceUtils';

function ShimmerOverlay() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]">
      <div className="absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-white/55 to-transparent animate-design-shimmer-sweep" />
    </div>
  );
}

function SpecSkeleton() {
  return (
    <div className="space-y-3">
      <div className="h-3 w-24 rounded bg-neutral-200/80 animate-design-skeleton-pulse" />
      <div className="flex gap-1.5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-6 w-6 rounded-md bg-neutral-200/90 animate-design-skeleton-pulse"
            style={{ animationDelay: `${i * 90}ms` }}
          />
        ))}
      </div>
      <div className="space-y-1.5 pt-1">
        <div className="h-2.5 w-full rounded bg-neutral-100 animate-design-skeleton-pulse" />
        <div className="h-2.5 w-4/5 rounded bg-neutral-100 animate-design-skeleton-pulse" />
        <div className="h-2.5 w-3/5 rounded bg-neutral-100 animate-design-skeleton-pulse" />
      </div>
      <div className="flex flex-wrap gap-1.5 pt-1">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-5 w-14 rounded-lg bg-neutral-100 animate-design-skeleton-pulse"
            style={{ animationDelay: `${i * 70}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

export function SpecCardNode({ data }: NodeProps) {
  const d = data as SpecData;
  if (d.phase === 'placeholder') {
    return (
      <div className="relative w-[300px] overflow-hidden rounded-2xl border border-indigo-100/80 bg-white p-3.5 shadow-md animate-design-card-in">
        <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
        <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="min-w-0 truncate text-[10px] font-bold uppercase tracking-wider text-indigo-400">
            Design specification
          </p>
          <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-500">
            <Loader2 size={10} className="animate-spin" />
            {d.label || 'Crafting…'}
          </span>
        </div>
        <div className="relative overflow-hidden rounded-xl border border-indigo-50/80 p-3 design-craft-surface">
          <SpecSkeleton />
          <ShimmerOverlay />
        </div>
      </div>
    );
  }

  const spec = d.spec || {};
  const colors = spec.colors || {};
  return (
    <div className="w-[300px] rounded-2xl border border-outline-variant/30 bg-white p-3.5 shadow-md animate-design-card-in">
      <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
      <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
        Design specification
      </p>
      <h3 className="mb-2 text-[14px] font-bold text-neutral-900">{spec.name || 'Spec'}</h3>
      {spec.rationale ? (
        <p className="mb-2.5 text-[11px] leading-relaxed text-neutral-500">{spec.rationale}</p>
      ) : null}
      <div className="space-y-2.5">
        {Object.entries(colors).map(([group, values]) => (
          <div key={group}>
            <p className="mb-1 text-[10px] font-semibold capitalize text-neutral-400">{group}</p>
            <div className="flex flex-wrap gap-1.5">
              {(values || []).map((hex) => (
                <div
                  key={`${group}-${hex}`}
                  className="h-6 w-6 rounded-md border border-black/5 shadow-sm"
                  style={{ background: hex }}
                  title={hex}
                />
              ))}
            </div>
          </div>
        ))}
        {spec.typography?.samples?.length ? (
          <div>
            <p className="mb-1 text-[10px] font-semibold text-neutral-400">Typography</p>
            <div className="space-y-1">
              {spec.typography.samples.map((sample, i) => (
                <p
                  key={i}
                  className="text-neutral-800"
                  style={{
                    fontFamily: spec.typography?.fontFamily,
                    fontSize: sample.size || '13px',
                    fontWeight: Number(sample.weight) || 400,
                  }}
                >
                  Aa · {sample.label}
                </p>
              ))}
            </div>
          </div>
        ) : null}
        {spec.components?.length ? (
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {spec.components.map((c) => (
              <span
                key={c}
                className="rounded-lg border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] text-neutral-600"
              >
                {c}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
