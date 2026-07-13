import React, { useEffect, useState } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Loader2, Pencil, Trash2 } from 'lucide-react';
import { useLanguage } from '../../LanguageContext';
import { sidecarAuthedHttpUrl } from '../../../services/sidecarUrl';
import {
  deviceView,
  ensureCharset,
  withPickerScript,
  type UiData,
} from '../designWorkspaceUtils';

function ShimmerOverlay() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]">
      <div className="absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-white/55 to-transparent animate-design-shimmer-sweep" />
    </div>
  );
}

export function UiCardNode({ data, selected }: NodeProps) {
  const { t } = useLanguage();
  const d = data as UiData;
  const view = deviceView(d.device);
  const scale = view.frameW / view.designW;
  const [resolvedPreviewSrc, setResolvedPreviewSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!d.previewSrc || d.pickMode) {
      setResolvedPreviewSrc(null);
      return;
    }
    void sidecarAuthedHttpUrl(d.previewSrc).then((url) => {
      if (!cancelled) setResolvedPreviewSrc(url);
    });
    return () => {
      cancelled = true;
    };
  }, [d.previewSrc, d.pickMode]);

  const useRemotePreview = Boolean(resolvedPreviewSrc) && !d.pickMode;
  if (d.phase === 'placeholder') {
    return (
      <div
        className={`relative overflow-hidden rounded-2xl border border-violet-100/90 bg-white shadow-md animate-design-card-in ${
          selected ? 'ring-2 ring-sky-500 ring-offset-2' : ''
        }`}
        style={{ width: view.frameW }}
      >
        <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
        <div className="flex items-center justify-between gap-2 border-b border-violet-50 px-3 py-2">
          <p className="min-w-0 truncate text-[12px] font-semibold text-neutral-700">{d.name || 'Interface'}</p>
          <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap text-[10px] font-medium text-violet-500">
            <Loader2 size={11} className="animate-spin" />
            {d.label || 'Generating…'}
          </span>
        </div>
        <div
          className="relative overflow-hidden design-craft-surface"
          style={{ height: Math.min(view.frameH, 320) }}
        >
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
            <div className="h-10 w-10 rounded-full border-2 border-violet-200 border-t-violet-500 animate-spin" />
            <p className="text-[12px] font-medium text-violet-500/90">
              {d.label || 'Sketching…'}
            </p>
            <p className="text-[10px] text-neutral-400">
              {d.device === 'app' ? '390 × 844' : '1920 × 1080'}
            </p>
          </div>
          <ShimmerOverlay />
        </div>
      </div>
    );
  }

  const drawing = d.phase === 'drawing';
  const pickMode = Boolean(d.pickMode);
  const hasElement = Boolean(d.selectedElementPath || d.selectedElementLabel);
  const selectedRing = selected
    ? hasElement
      ? 'border-sky-200 shadow-md'
      : 'ring-2 ring-sky-500 ring-offset-2 border-sky-300'
    : 'border-outline-variant/30';
  return (
    <div
      className={`overflow-hidden rounded-2xl border bg-white shadow-md animate-design-card-in ${selectedRing}`}
      style={{ width: view.frameW }}
    >
      <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
      <div className="flex items-center justify-between gap-2 border-b border-neutral-100 px-3 py-2">
        <div className="min-w-0">
          <p className="truncate text-[12px] font-semibold text-neutral-800">{d.name}</p>
          <p className="text-[9px] font-medium uppercase tracking-wide text-neutral-400">
            {d.device === 'app' ? 'Mobile · 390×844' : 'Web · 1920×1080'}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {drawing ? (
            <span className="inline-flex items-center gap-1 whitespace-nowrap text-[10px] font-medium text-violet-500">
              <Loader2 size={11} className="animate-spin" />
              {d.label || 'Generating…'}
            </span>
          ) : (
            <>
              {selected && d.onDelete ? (
                <button
                  type="button"
                  className="nodrag nopan inline-flex h-6 w-6 items-center justify-center rounded-md text-neutral-400 hover:bg-rose-100 hover:text-rose-600 transition-colors"
                  title={t('Delete screen')}
                  aria-label={t('Delete screen')}
                  onClick={(e) => {
                    e.stopPropagation();
                    d.onDelete?.();
                  }}
                >
                  <Trash2 size={12} strokeWidth={2.25} />
                </button>
              ) : null}
              <button
                type="button"
                className={`nodrag nopan inline-flex h-6 w-6 items-center justify-center rounded-md transition-colors ${
                  pickMode
                    ? 'bg-sky-600 text-white'
                    : hasElement
                      ? 'bg-sky-100 text-sky-700'
                      : 'text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700'
                }`}
                title={pickMode ? t('Picking…') : t('Pick element')}
                aria-label={pickMode ? t('Picking…') : t('Pick element')}
                aria-pressed={pickMode}
                onClick={(e) => {
                  e.stopPropagation();
                  d.onTogglePick?.();
                }}
              >
                <Pencil size={12} strokeWidth={2.25} />
              </button>
              {pickMode ? (
                <span className="whitespace-nowrap text-[10px] font-medium text-sky-600">{t('Picking…')}</span>
              ) : hasElement ? (
                <span className="max-w-[120px] truncate whitespace-nowrap text-[10px] font-medium text-sky-700">
                  {d.selectedElementLabel}
                </span>
              ) : (
                <span className="text-[10px] text-emerald-600">Ready</span>
              )}
            </>
          )}
        </div>
      </div>
      <div
        className={`relative overflow-hidden bg-neutral-100 ${
          hasElement && !pickMode ? 'ring-1 ring-inset ring-sky-200' : ''
        }`}
        style={{ width: view.frameW, height: view.frameH }}
      >
        {d.html || resolvedPreviewSrc ? (
          <>
            {useRemotePreview ? (
              <iframe
                key={`remote-${resolvedPreviewSrc}`}
                title={d.name}
                src={resolvedPreviewSrc!}
                className={`absolute left-0 top-0 origin-top-left border-0 bg-white ${
                  drawing || !pickMode ? 'pointer-events-none' : 'pointer-events-auto'
                } ${drawing ? 'animate-design-draw-reveal' : ''}`}
                style={{
                  width: view.designW,
                  height: view.designH,
                  transform: `scale(${scale})`,
                }}
              />
            ) : (
              <iframe
                key={`local-${pickMode}-${d.html ? d.html.length : 0}`}
                title={d.name}
                sandbox="allow-scripts"
                srcDoc={ensureCharset(withPickerScript(d.html || '', {
                  pickMode,
                  selectedPath: d.selectedElementPath,
                }))}
                className={`absolute left-0 top-0 origin-top-left border-0 bg-white ${
                  drawing || !pickMode ? 'pointer-events-none' : 'pointer-events-auto'
                } ${drawing ? 'animate-design-draw-reveal' : ''}`}
                style={{
                  width: view.designW,
                  height: view.designH,
                  transform: `scale(${scale})`,
                }}
              />
            )}
            {!pickMode ? (
              <div className="nodrag absolute inset-0 z-[1]" />
            ) : null}
          </>
        ) : null}
        {drawing ? (
          <>
            <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center bg-violet-50/60 backdrop-blur-[1px]">
              <div className="flex flex-col items-center gap-2">
                <Loader2 size={22} className="animate-spin text-violet-500" />
                <span className="max-w-[180px] text-center text-[12px] font-semibold text-violet-700">
                  {d.label || 'Generating…'}
                </span>
              </div>
            </div>
            <div className="pointer-events-none absolute inset-x-0 top-0 z-20 h-1 overflow-hidden">
              <div className="h-full w-1/3 bg-violet-400/80 animate-design-shimmer-sweep" />
            </div>
          </>
        ) : null}
        {pickMode && !hasElement ? (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-sky-600/15 to-transparent px-3 py-2">
            <p className="text-center text-[10px] font-medium text-sky-700">{t('Click a component')}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
