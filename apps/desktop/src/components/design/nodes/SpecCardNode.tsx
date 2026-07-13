import React, { useState, useRef, useEffect } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Loader2, Save } from 'lucide-react';
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

function SaveStylePopover({ defaultName, onSave, onClose }: { defaultName: string; onSave: (name: string) => void; onClose: () => void }) {
  const [name, setName] = useState(defaultName);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    onSave(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  };

  return (
    <div
      className="nodrag nopan absolute right-0 top-full z-50 mt-1 w-52 rounded-xl border border-neutral-200 bg-white shadow-md"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={handleKeyDown}
    >
      <form onSubmit={handleSubmit} className="p-3 space-y-2">
        <input
          ref={inputRef}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-1.5 text-[12px] text-neutral-900 placeholder-neutral-400 focus:border-neutral-300 focus:outline-none focus:ring-1 focus:ring-neutral-300"
          placeholder="Style name"
        />
        <div className="flex justify-end gap-1.5">
          <button
            type="button"
            className="rounded-lg px-2.5 py-1 text-[11px] font-medium text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="rounded-lg bg-neutral-900 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-black transition-colors disabled:opacity-40"
            disabled={!name.trim()}
          >
            Save
          </button>
        </div>
      </form>
    </div>
  );
}

export function SpecCardNode({ data }: NodeProps) {
  const d = data as SpecData;
  const [showSavePopover, setShowSavePopover] = useState(false);
  const saveBtnRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showSavePopover) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (popoverRef.current?.contains(target)) return;
      if (saveBtnRef.current?.contains(target)) return;
      setShowSavePopover(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showSavePopover]);
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
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">
          Design specification
        </p>
        {d.onSaveStyle && d.designMdText ? (
          <div className="relative">
            <button
              ref={saveBtnRef}
              type="button"
              className="nodrag nopan shrink-0 rounded-md p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 transition-colors"
              onClick={(e) => { e.stopPropagation(); setShowSavePopover((v) => !v); }}
              title="Save as custom style"
              aria-label="Save as custom style"
            >
              <Save size={14} />
            </button>
            {showSavePopover ? (
              <div ref={popoverRef}>
                <SaveStylePopover
                  defaultName={spec.name || 'Custom Style'}
                  onSave={(name) => { d.onSaveStyle?.(name, d.designMdText!); setShowSavePopover(false); }}
                  onClose={() => setShowSavePopover(false)}
                />
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
      <h3 className="mb-2 text-[14px] font-bold text-neutral-900">{spec.name || 'Spec'}</h3>
      {spec.rationale ? (
        <p className="mb-2.5 text-[11px] leading-relaxed text-neutral-500">{spec.rationale}</p>
      ) : null}
      <div className="space-y-2.5">
        {Object.entries(colors).map(([group, values]) => {
          const hexList = Array.isArray(values)
            ? values
            : typeof values === 'string'
              ? [values]
              : Array.isArray(values?.primary)
                ? values.primary
                : [];
          return (
          <div key={group}>
            <p className="mb-1 text-[10px] font-semibold capitalize text-neutral-400">{group}</p>
            <div className="flex flex-wrap gap-1.5">
              {hexList.map((hex) => (
                <div
                  key={`${group}-${hex}`}
                  className="h-6 w-6 rounded-md border border-black/5 shadow-sm"
                  style={{ background: hex }}
                  title={hex}
                />
              ))}
            </div>
          </div>
          );
        })}
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
