import React, { useEffect, useState } from 'react';
import { Paperclip } from 'lucide-react';
import type { DispatchEdge } from '../../types';
import { useLanguage } from '../LanguageContext';
import { HandoffPreviewModal } from './HandoffPreviewModal';

interface HandoffLinkOverlayProps {
  edges: DispatchEdge[];
  paneRefs: Map<string, HTMLDivElement>;
  stageRef: React.RefObject<HTMLDivElement | null>;
  refTick?: number;
  hoverEdge: DispatchEdge | null;
  onHoverEdge: (edge: DispatchEdge | null) => void;
  onSendToBar: (text: string) => void;
}

type LineSegment = {
  edge: DispatchEdge;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  mx: number;
  my: number;
};

function computeSegments(
  edges: DispatchEdge[],
  paneRefs: Map<string, HTMLDivElement>,
  stageEl: HTMLDivElement | null,
): LineSegment[] {
  if (!stageEl || edges.length === 0) return [];
  const stageRect = stageEl.getBoundingClientRect();
  const segments: LineSegment[] = [];

  for (const edge of edges) {
    const targetEl = paneRefs.get(edge.target_lane_id);
    if (!targetEl) continue;
    const targetRect = targetEl.getBoundingClientRect();
    const tx = targetRect.left + targetRect.width / 2 - stageRect.left;
    const ty = targetRect.top - stageRect.top;

    for (const sourceLaneId of edge.source_lane_ids) {
      const sourceEl = paneRefs.get(sourceLaneId);
      if (!sourceEl) continue;
      const sourceRect = sourceEl.getBoundingClientRect();
      const sx = sourceRect.left + sourceRect.width / 2 - stageRect.left;
      const sy = sourceRect.bottom - stageRect.top;
      segments.push({
        edge,
        x1: sx,
        y1: sy,
        x2: tx,
        y2: ty,
        mx: (sx + tx) / 2,
        my: (sy + ty) / 2,
      });
    }
  }
  return segments;
}

export const HandoffLinkOverlay: React.FC<HandoffLinkOverlayProps> = ({
  edges,
  paneRefs,
  stageRef,
  refTick = 0,
  hoverEdge,
  onHoverEdge,
  onSendToBar,
}) => {
  const { t } = useLanguage();
  const [segments, setSegments] = useState<LineSegment[]>([]);
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const [cardPos, setCardPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const update = () => {
      setSegments(computeSegments(edges, paneRefs, stageRef.current));
    };
    update();
    const observer = new ResizeObserver(update);
    if (stageRef.current) observer.observe(stageRef.current);
    window.addEventListener('resize', update);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', update);
    };
  }, [edges, paneRefs, stageRef, refTick]);

  if (segments.length === 0) return null;

  const activeEdge = hoverEdge;

  return (
    <>
      <div
        data-testid="handoff-links-layer"
        className="pointer-events-none absolute inset-0 z-20"
        aria-hidden={!activeEdge}
      >
        <svg className="absolute inset-0 w-full h-full overflow-visible">
          {segments.map((seg, i) => (
            <line
              key={`${seg.edge.handoff_file}-${i}`}
              x1={seg.x1}
              y1={seg.y1}
              x2={seg.x2}
              y2={seg.y2}
              stroke="currentColor"
              className="text-neutral-900"
              strokeWidth={1.5}
              strokeDasharray="6 4"
            />
          ))}
        </svg>
        {segments.map((seg, i) => (
          <button
            key={`marker-${seg.edge.handoff_file}-${i}`}
            type="button"
            className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 w-5 h-5 rounded-full border border-outline-variant bg-surface-bright shadow-sm flex items-center justify-center text-on-surface hover:bg-surface-container-high"
            style={{ left: seg.mx, top: seg.my }}
            title={seg.edge.handoff_file}
            onMouseEnter={() => {
              onHoverEdge(seg.edge);
              setCardPos({ x: seg.mx, y: seg.my });
            }}
            onMouseLeave={() => onHoverEdge(null)}
            onClick={() => setPreviewPath(`.clutch/handoffs/${seg.edge.handoff_file}`)}
          >
            <Paperclip className="w-2.5 h-2.5" />
          </button>
        ))}
      </div>

      {activeEdge ? (
        <div
          className="absolute z-30 pointer-events-auto rounded-xl border border-outline-variant bg-surface-bright shadow-lg p-3 text-[10px] max-w-[220px]"
          style={{ left: cardPos.x + 12, top: cardPos.y - 8 }}
          onMouseLeave={() => onHoverEdge(null)}
        >
          <p className="font-semibold text-on-surface-variant mb-1">{activeEdge.handoff_file}</p>
          <p className="text-on-surface mb-2">
            {activeEdge.sources.join(' + ')} → {activeEdge.target}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              className="flex-1 px-2 py-1 rounded-lg border border-outline-variant/40 bg-surface-container-low hover:bg-surface-container-high"
              onClick={() => setPreviewPath(`.clutch/handoffs/${activeEdge.handoff_file}`)}
            >
              {t('Preview handoff')}
            </button>
            <button
              type="button"
              className="flex-1 px-2 py-1 rounded-lg border border-outline-variant/40 bg-surface-container-low hover:bg-surface-container-high"
              onClick={() => onSendToBar(`@${activeEdge.target} 参考 handoff @${activeEdge.handoff_file}`)}
            >
              {t('Send to Bar')}
            </button>
          </div>
        </div>
      ) : null}

      {previewPath ? (
        <HandoffPreviewModal path={previewPath} onClose={() => setPreviewPath(null)} />
      ) : null}
    </>
  );
};
