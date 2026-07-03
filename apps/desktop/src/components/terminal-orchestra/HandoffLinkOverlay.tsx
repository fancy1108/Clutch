import React, { useEffect, useState } from 'react';
import { Paperclip } from 'lucide-react';
import type { DispatchEdge } from '../../types';
import { useLanguage } from '../LanguageContext';
import { BTN_PRIMARY_SM, BTN_SECONDARY_SM } from '../ui/buttonStyles';
import { HandoffPreviewModal } from './HandoffPreviewModal';

interface HandoffLinkOverlayProps {
  edges: DispatchEdge[];
  paneRefs: React.RefObject<Map<string, HTMLDivElement>>;
  stageRef: React.RefObject<HTMLDivElement | null>;
  refTick?: number;
  hoverEdge: DispatchEdge | null;
  onHoverEdge: (edge: DispatchEdge | null) => void;
  onSendToBar: (text: string) => void;
}

type Point = { x: number; y: number };

type LineSegment = {
  edge: DispatchEdge;
  mx: number;
  my: number;
  path: Point[];
};

type StageRect = { left: number; top: number };
type PaneRect = { left: number; top: number; right: number; bottom: number; width: number; height: number };

/** Gap reserved at path midpoint for the attachment button. */
const CENTER_ATTACH_GAP_PX = 10;
const ROUTE_PAD_PX = 6;

function paneRect(el: DOMRect, stage: StageRect): PaneRect {
  return {
    left: el.left - stage.left,
    top: el.top - stage.top,
    right: el.right - stage.left,
    bottom: el.bottom - stage.top,
    width: el.width,
    height: el.height,
  };
}

function insetRect(rect: PaneRect, pad: number): PaneRect {
  return {
    left: rect.left + pad,
    top: rect.top + pad,
    right: rect.right - pad,
    bottom: rect.bottom - pad,
    width: Math.max(0, rect.width - pad * 2),
    height: Math.max(0, rect.height - pad * 2),
  };
}

/** Pick nearest edge midpoints between two lane panes. */
function closestConnectPoints(source: PaneRect, target: PaneRect): { start: Point; end: Point } {
  const scx = source.left + source.width / 2;
  const scy = source.top + source.height / 2;
  const tcx = target.left + target.width / 2;
  const tcy = target.top + target.height / 2;
  const dx = tcx - scx;
  const dy = tcy - scy;

  if (Math.abs(dx) >= Math.abs(dy)) {
    if (dx >= 0) {
      return { start: { x: source.right, y: scy }, end: { x: target.left, y: tcy } };
    }
    return { start: { x: source.left, y: scy }, end: { x: target.right, y: tcy } };
  }
  if (dy >= 0) {
    return { start: { x: scx, y: source.bottom }, end: { x: tcx, y: target.top } };
  }
  return { start: { x: scx, y: source.top }, end: { x: tcx, y: target.bottom } };
}

function segmentIntersectsRect(a: Point, b: Point, rect: PaneRect): boolean {
  const minX = Math.min(a.x, b.x);
  const maxX = Math.max(a.x, b.x);
  const minY = Math.min(a.y, b.y);
  const maxY = Math.max(a.y, b.y);
  if (maxX < rect.left || minX > rect.right || maxY < rect.top || minY > rect.bottom) {
    return false;
  }
  if (a.x === b.x) {
    return a.x >= rect.left && a.x <= rect.right && maxY >= rect.top && minY <= rect.bottom;
  }
  if (a.y === b.y) {
    return a.y >= rect.top && a.y <= rect.bottom && maxX >= rect.left && minX <= rect.right;
  }
  return true;
}

function pathHitsObstacle(points: Point[], obstacles: PaneRect[]): boolean {
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    for (const obstacle of obstacles) {
      if (segmentIntersectsRect(a, b, obstacle)) return true;
    }
  }
  return false;
}

/** Orthogonal route through lane gaps when a direct edge line crosses another pane. */
function routeHandoffPath(
  source: PaneRect,
  target: PaneRect,
  obstacles: PaneRect[],
): Point[] {
  const { start, end } = closestConnectPoints(source, target);
  const direct = [start, end];
  if (!pathHitsObstacle(direct, obstacles)) return direct;

  const scx = source.left + source.width / 2;
  const scy = source.top + source.height / 2;
  const tcx = target.left + target.width / 2;
  const tcy = target.top + target.height / 2;
  const gapX = (Math.max(source.right, target.right) + Math.min(source.left, target.left)) / 2;
  const gapY = (Math.max(source.bottom, target.bottom) + Math.min(source.top, target.top)) / 2;

  const candidates: Point[][] = [
    [start, { x: gapX, y: start.y }, { x: gapX, y: end.y }, end],
    [start, { x: start.x, y: gapY }, { x: end.x, y: gapY }, end],
    [start, { x: start.x, y: end.y }, end],
    [start, { x: end.x, y: start.y }, end],
    [start, { x: scx, y: gapY }, { x: tcx, y: gapY }, end],
    [start, { x: gapX, y: scy }, { x: gapX, y: tcy }, end],
  ];

  for (const candidate of candidates) {
    if (!pathHitsObstacle(candidate, obstacles)) return candidate;
  }
  return direct;
}

function pathMidpoint(points: Point[]): Point {
  let total = 0;
  for (let i = 0; i < points.length - 1; i += 1) {
    total += Math.hypot(points[i + 1].x - points[i].x, points[i + 1].y - points[i].y);
  }
  const half = total / 2;
  let walked = 0;
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const segLen = Math.hypot(b.x - a.x, b.y - a.y);
    if (walked + segLen >= half) {
      const t = segLen > 0 ? (half - walked) / segLen : 0;
      return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
    }
    walked += segLen;
  }
  return points[points.length - 1];
}

function splitPathAtCenter(points: Point[], centerGapPx: number): { mid: Point; before: Point[]; after: Point[] } {
  if (points.length < 2) {
    const only = points[0] ?? { x: 0, y: 0 };
    return { mid: only, before: [only], after: [only] };
  }

  let total = 0;
  for (let i = 0; i < points.length - 1; i += 1) {
    total += Math.hypot(points[i + 1].x - points[i].x, points[i + 1].y - points[i].y);
  }
  const halfGap = centerGapPx / 2;
  const midAt = total / 2;
  let walked = 0;
  const before: Point[] = [points[0]];
  const after: Point[] = [];

  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const segLen = Math.hypot(b.x - a.x, b.y - a.y);
    if (walked + segLen >= midAt - halfGap) {
      const tStart = segLen > 0 ? Math.max(0, (midAt - halfGap - walked) / segLen) : 0;
      const tEnd = segLen > 0 ? Math.min(1, (midAt + halfGap - walked) / segLen) : 1;
      const gapStart = { x: a.x + (b.x - a.x) * tStart, y: a.y + (b.y - a.y) * tStart };
      const gapEnd = { x: a.x + (b.x - a.x) * tEnd, y: a.y + (b.y - a.y) * tEnd };
      before.push(gapStart);
      after.push(gapEnd);
      for (let j = i + 1; j < points.length; j += 1) after.push(points[j]);
      return { mid: pathMidpoint(points), before, after };
    }
    walked += segLen;
    before.push(b);
  }

  const end = points[points.length - 1];
  return { mid: end, before: points, after: [end] };
}

function pointsToPolyline(points: Point[]): string {
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
}

function computeSegments(
  edges: DispatchEdge[],
  paneRefs: Map<string, HTMLDivElement>,
  stageEl: HTMLDivElement | null,
): LineSegment[] {
  if (!stageEl || edges.length === 0) return [];
  try {
    const stageDom = stageEl.getBoundingClientRect();
    const stage: StageRect = { left: stageDom.left, top: stageDom.top };
    const allRects = new Map<string, PaneRect>();
    for (const [laneId, el] of paneRefs.entries()) {
      allRects.set(laneId, paneRect(el.getBoundingClientRect(), stage));
    }

    const segments: LineSegment[] = [];

    for (const edge of edges) {
      const targetRect = allRects.get(edge.target_lane_id);
      if (!targetRect) continue;
      const targetInset = insetRect(targetRect, ROUTE_PAD_PX);

      for (const sourceLaneId of edge.source_lane_ids ?? []) {
        const sourceRect = allRects.get(sourceLaneId);
        if (!sourceRect) continue;
        const sourceInset = insetRect(sourceRect, ROUTE_PAD_PX);
        const obstacles = [...allRects.entries()]
          .filter(([laneId]) => laneId !== sourceLaneId && laneId !== edge.target_lane_id)
          .map(([, rect]) => insetRect(rect, ROUTE_PAD_PX));
        const path = routeHandoffPath(sourceInset, targetInset, obstacles);
        const { mid } = splitPathAtCenter(path, CENTER_ATTACH_GAP_PX);
        segments.push({ edge, mx: mid.x, my: mid.y, path });
      }
    }
    return segments;
  } catch {
    return [];
  }
}

function edgeKey(edge: DispatchEdge): string {
  return `${edge.handoff_file}:${edge.target_lane_id}`;
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
  const [pinnedEdge, setPinnedEdge] = useState<DispatchEdge | null>(null);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        const next = computeSegments(edges, paneRefs.current, stageRef.current);
        setSegments((prev) => {
          if (
            prev.length === next.length
            && prev.every((seg, index) => {
              const other = next[index];
              return (
                other
                && edgeKey(seg.edge) === edgeKey(other.edge)
                && seg.mx === other.mx
                && seg.my === other.my
              );
            })
          ) {
            return prev;
          }
          return next;
        });
      });
    };
    update();
    const observer = new ResizeObserver(update);
    if (stageRef.current) observer.observe(stageRef.current);
    window.addEventListener('resize', update);
    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('resize', update);
    };
  }, [edges, paneRefs, stageRef, refTick]);

  useEffect(() => {
    if (pinnedEdge && !edges.some((edge) => edgeKey(edge) === edgeKey(pinnedEdge))) {
      setPinnedEdge(null);
    }
  }, [edges, pinnedEdge]);

  if (segments.length === 0) return null;

  const displayedEdge = pinnedEdge ?? hoverEdge;

  const togglePin = (edge: DispatchEdge) => {
    setPinnedEdge((current) => (current && edgeKey(current) === edgeKey(edge) ? null : edge));
  };

  const clearHoverUnlessPinned = (edge: DispatchEdge) => {
    if (pinnedEdge && edgeKey(pinnedEdge) === edgeKey(edge)) return;
    onHoverEdge(null);
  };

  return (
    <>
      <div
        data-testid="handoff-links-layer"
        className="pointer-events-none absolute inset-0 z-20"
        aria-hidden={!displayedEdge}
      >
        <svg className="absolute inset-0 w-full h-full overflow-visible">
          <defs>
            <marker
              id="handoff-arrow"
              markerWidth="6"
              markerHeight="6"
              refX="5"
              refY="3"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M0,0 L0,6 L6,3 z" fill="currentColor" />
            </marker>
          </defs>
          {segments.map((seg, i) => {
            const { before, after } = splitPathAtCenter(seg.path, CENTER_ATTACH_GAP_PX);
            return (
              <g key={`${seg.edge.handoff_file}-${i}`} className="text-neutral-400">
                <path
                  d={pointsToPolyline(before)}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1}
                />
                <path
                  d={pointsToPolyline(after)}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1}
                  markerEnd="url(#handoff-arrow)"
                />
              </g>
            );
          })}
        </svg>
        {segments.map((seg, i) => {
          const isActive = displayedEdge ? edgeKey(displayedEdge) === edgeKey(seg.edge) : false;
          return (
            <div
              key={`marker-${seg.edge.handoff_file}-${i}`}
              className="pointer-events-auto absolute -translate-x-1/2 -translate-y-1/2 z-[21]"
              style={{ left: seg.mx, top: seg.my }}
              onMouseEnter={() => onHoverEdge(seg.edge)}
              onMouseLeave={() => clearHoverUnlessPinned(seg.edge)}
            >
              <button
                type="button"
                className={`inline-flex items-center justify-center w-4 h-4 rounded-full border transition-colors shadow-sm ${
                  isActive
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-900 bg-white text-neutral-900 hover:bg-neutral-100'
                }`}
                title={seg.edge.handoff_file}
                aria-expanded={isActive}
                onClick={() => togglePin(seg.edge)}
              >
                <Paperclip className="w-2 h-2" strokeWidth={2.25} />
              </button>
              {isActive ? (
                <div
                  className="absolute left-1/2 bottom-[calc(100%+8px)] -translate-x-1/2 min-w-[220px] max-w-[280px] rounded-2xl border border-outline-variant/30 bg-surface-bright shadow-lg p-3 text-[10px] z-[22]"
                  onMouseEnter={() => onHoverEdge(seg.edge)}
                  onMouseLeave={() => clearHoverUnlessPinned(seg.edge)}
                >
                  <p className="font-mono text-[9px] text-on-surface-variant break-all mb-1.5">
                    {seg.edge.handoff_file}
                  </p>
                  <p className="font-semibold text-on-surface mb-2.5">
                    {(seg.edge.sources ?? []).join(' + ')} → {seg.edge.target}
                  </p>
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      className={`${BTN_SECONDARY_SM} flex-1`}
                      onClick={() => setPreviewPath(`.clutch/handoffs/${seg.edge.handoff_file}`)}
                    >
                      {t('Preview handoff')}
                    </button>
                    <button
                      type="button"
                      className={`${BTN_PRIMARY_SM} flex-1`}
                      onClick={() => {
                        onSendToBar(`@${seg.edge.target} 参考 handoff @${seg.edge.handoff_file}`);
                        setPinnedEdge(null);
                        onHoverEdge(null);
                      }}
                    >
                      {t('Send to Bar')}
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {previewPath ? (
        <HandoffPreviewModal path={previewPath} onClose={() => setPreviewPath(null)} />
      ) : null}
    </>
  );
};
