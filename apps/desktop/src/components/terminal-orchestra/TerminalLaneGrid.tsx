import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { DispatchEdge, PtyLane } from '../../types';
import { clutchStore } from '../../services/clutchState';
import {
  buildPreviewPtyLane,
  collapsedLanes,
  computeLaneGridPageCount,
  computeLaneLayout,
  expandedLanes,
  laneGridPageIndex,
  orderLanesForGrid,
  sliceLanesForGridPage,
  uniqueLanesByLaneId,
} from '../../services/terminalOrchestraUtils';
import { TerminalLanePane } from './TerminalLanePane';
import { TerminalLaneFloatRail } from './TerminalLaneFloatRail';
import { HandoffLinkOverlay } from './HandoffLinkOverlay';
import { useLanguage } from '../LanguageContext';
import {
  expandedLaneSlot,
  lanePaneOuterClass,
  LANE_KEEPALIVE_SLOT,
  scheduleTerminalLayoutRefit,
} from './terminalLaneLayout';

interface TerminalLaneGridProps {
  lanes: PtyLane[];
  dispatchEdges: DispatchEdge[];
  sessionRunId: string;
  visible: boolean;
  barFocused: boolean;
  configuredAgents: Array<{ name: string; agentType?: string }>;
  /** True after confirm dispatch — use persisted lanes from state. */
  sessionDispatched?: boolean;
  /** Before first dispatch: show a live preview for the @-mentioned agent. */
  previewAgentType?: string | null;
  previewAgentId?: string | null;
  previewAgentName?: string | null;
  layoutChromeKey?: string;
  layoutObserveRef?: React.RefObject<HTMLElement | null>;
  onOpenWorkspaceFile?: (path: string) => void;
}

export const TerminalLaneGrid: React.FC<TerminalLaneGridProps> = ({
  lanes,
  dispatchEdges,
  sessionRunId,
  visible,
  barFocused,
  configuredAgents,
  sessionDispatched = false,
  previewAgentType = null,
  previewAgentId = null,
  previewAgentName = null,
  layoutChromeKey = '',
  layoutObserveRef,
  onOpenWorkspaceFile,
}) => {
  const { t } = useLanguage();
  const paneRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const stageRef = useRef<HTMLDivElement>(null);
  const laneRowRef = useRef<HTMLDivElement>(null);
  const lastStageSizeRef = useRef<{ width: number; height: number } | null>(null);
  const [handoffHover, setHandoffHover] = useState<DispatchEdge | null>(null);
  const [layoutTick, setLayoutTick] = useState(0);
  const [previewCollapsed, setPreviewCollapsed] = useState(false);
  const [gridPage, setGridPage] = useState(0);

  const bumpLayoutTick = useCallback(() => {
    setLayoutTick((n) => n + 1);
  }, []);

  const scheduleLayoutRefit = useCallback(() => {
    return scheduleTerminalLayoutRefit(bumpLayoutTick);
  }, [bumpLayoutTick]);

  const displayLanes = useMemo(() => {
    if (sessionDispatched) {
      return uniqueLanesByLaneId(lanes);
    }
    if (!previewAgentType) return [];
    const preview = buildPreviewPtyLane(previewAgentType, sessionRunId);
    const stateLane = lanes.find((lane) => lane.lane_id === preview.lane_id);
    return [{
      ...preview,
      collapsed: stateLane?.collapsed ?? previewCollapsed,
      focused: stateLane?.focused ?? preview.focused,
      status: stateLane?.status ?? preview.status,
    }];
  }, [lanes, previewAgentType, previewCollapsed, sessionRunId, sessionDispatched]);

  useEffect(() => {
    setPreviewCollapsed(false);
  }, [previewAgentType, sessionRunId, sessionDispatched]);

  const handoffEdgesBase = displayLanes.length >= 2 ? dispatchEdges : [];

  const expanded = expandedLanes(displayLanes);
  const collapsed = collapsedLanes(displayLanes);
  const pageCount = computeLaneGridPageCount(expanded.length);
  const needsPagination = pageCount > 1;
  const safeGridPage = Math.min(gridPage, Math.max(0, pageCount - 1));
  const baseLayout = computeLaneLayout(Math.max(1, expanded.length));
  const expandedOrdered = orderLanesForGrid(
    expanded.length > 0 ? expanded : displayLanes,
    needsPagination ? 'quad' : baseLayout,
  );
  const pageLanes = needsPagination
    ? sliceLanesForGridPage(expandedOrdered, safeGridPage)
    : expandedOrdered;
  const layout = computeLaneLayout(Math.max(1, pageLanes.length));
  const pageLanesOrdered = orderLanesForGrid(pageLanes, layout);
  const visibleLaneIds = useMemo(
    () => new Set(pageLanesOrdered.map((lane) => lane.lane_id)),
    [pageLanesOrdered],
  );
  const handoffEdges = handoffEdgesBase.filter(
    (edge) =>
      visibleLaneIds.has(edge.target_lane_id)
      && edge.source_lane_ids.every((laneId) => visibleLaneIds.has(laneId)),
  );
  const laneLayoutKey = useMemo(
    () => [
      layout,
      safeGridPage,
      displayLanes.map((lane) => `${lane.lane_id}:${lane.collapsed ? 1 : 0}:${lane.focused ? 1 : 0}`).join('|'),
    ].join('::'),
    [displayLanes, layout, safeGridPage],
  );

  useEffect(() => {
    if (!needsPagination) {
      setGridPage(0);
      return;
    }
    if (gridPage >= pageCount) {
      setGridPage(Math.max(0, pageCount - 1));
    }
  }, [gridPage, needsPagination, pageCount]);

  useEffect(() => {
    if (!needsPagination) return;
    const focusedLane = expandedOrdered.find((lane) => lane.focused);
    const focusedId = focusedLane?.lane_id ?? null;
    if (!focusedId) return;
    const focusedIndex = expandedOrdered.findIndex((lane) => lane.lane_id === focusedId);
    if (focusedIndex < 0) return;
    const targetPage = laneGridPageIndex(focusedIndex);
    setGridPage((current) => (current === targetPage ? current : targetPage));
  }, [
    needsPagination,
    expandedOrdered.map((lane) => `${lane.lane_id}:${lane.focused ? 1 : 0}`).join('|'),
  ]);

  const registerPane = useCallback((el: HTMLDivElement | null, laneId: string) => {
    const existing = paneRefs.current.get(laneId);
    if (el) {
      if (existing === el) return;
      paneRefs.current.set(laneId, el);
    } else {
      if (!existing) return;
      paneRefs.current.delete(laneId);
    }
    setLayoutTick((n) => n + 1);
  }, []);

  const handleFocus = (laneId: string) => {
    void clutchStore.focusLane(laneId);
  };

  const handleCollapse = (laneId: string) => {
    if (!sessionDispatched) {
      setPreviewCollapsed(true);
    }
    void clutchStore.collapseLane(laneId, true);
    scheduleLayoutRefit();
  };

  const handleExpand = (laneId: string) => {
    if (!sessionDispatched) {
      setPreviewCollapsed(false);
    }
    void clutchStore.collapseLane(laneId, false);
    void clutchStore.focusLane(laneId);
    if (needsPagination) {
      const expandedIndex = expandedOrdered.findIndex((lane) => lane.lane_id === laneId);
      if (expandedIndex >= 0) {
        setGridPage(laneGridPageIndex(expandedIndex));
      }
    }
    scheduleLayoutRefit();
  };

  const shell = `${lanePaneOuterClass(false)} h-full w-full`;

  useEffect(() => {
    return scheduleLayoutRefit();
  }, [layoutChromeKey, scheduleLayoutRefit]);

  useEffect(() => {
    if (!visible) return;
    return scheduleLayoutRefit();
  }, [visible, scheduleLayoutRefit]);

  useEffect(() => {
    const stage = stageRef.current;
    const outer = layoutObserveRef?.current ?? null;
    const row = laneRowRef.current;
    if (!stage && !outer && !row) return;

    const bump = () => {
      const target = row ?? stage;
      if (!target) return;
      const { width, height } = target.getBoundingClientRect();
      const last = lastStageSizeRef.current;
      if (
        last
        && Math.abs(last.width - width) < 1
        && Math.abs(last.height - height) < 1
      ) {
        return;
      }
      lastStageSizeRef.current = { width, height };
      setLayoutTick((n) => n + 1);
    };
    const observer = new ResizeObserver(bump);
    if (stage) observer.observe(stage);
    if (row) observer.observe(row);
    if (outer && outer !== stage) observer.observe(outer);
    window.addEventListener('resize', bump);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', bump);
    };
  }, [layoutObserveRef, layoutChromeKey, layout, laneLayoutKey]);

  useEffect(() => {
    return scheduleLayoutRefit();
  }, [displayLanes.length, expanded.length, collapsed.length, handoffEdges.length, layout, laneLayoutKey, scheduleLayoutRefit]);

  const queuedLanes = useMemo(
    () => lanes.filter((lane) => lane.status === 'queued'),
    [lanes],
  );

  return (
    <div data-testid="terminal-lane-grid" className="w-full flex flex-1 flex-col min-h-0 min-w-0">
      {queuedLanes.length > 0 ? (
        <div
          data-testid="orchestra-queue"
          className="flex flex-wrap gap-1.5 px-2 py-1.5 shrink-0 text-[10px] text-on-surface-variant"
        >
          {queuedLanes.map((lane) => (
            <span
              key={lane.lane_id}
              data-testid={`queued-lane-${lane.lane_id}`}
              className="px-2 py-0.5 rounded-md border border-dashed border-outline-variant/50 bg-surface-container-low"
            >
              {lane.label || lane.agent_type} · {t('Queued')}
            </span>
          ))}
        </div>
      ) : null}
      <div ref={stageRef} className="relative flex flex-1 flex-col min-h-0 min-w-0">
        {needsPagination ? (
          <div
            className="flex justify-center items-center gap-2 py-2 shrink-0"
            data-testid="terminal-lane-page-dots"
            role="tablist"
            aria-label={t('Terminal pages')}
          >
            {Array.from({ length: pageCount }, (_, pageIndex) => (
              <button
                key={pageIndex}
                type="button"
                role="tab"
                aria-selected={pageIndex === safeGridPage}
                aria-label={`${t('Terminal page')} ${pageIndex + 1}`}
                onClick={() => {
                  setGridPage(pageIndex);
                  scheduleLayoutRefit();
                }}
                className={`rounded-full transition-all ${
                  pageIndex === safeGridPage
                    ? 'w-2 h-2 bg-on-surface'
                    : 'w-1.5 h-1.5 bg-on-surface-variant/40 hover:bg-on-surface-variant/70'
                }`}
              />
            ))}
          </div>
        ) : null}
        <div className="flex flex-1 gap-2 min-h-0 min-w-0">
          <div ref={laneRowRef} className="relative flex flex-1 min-h-0 min-w-0">
            {displayLanes.map((lane) => {
              const paneKey = !sessionDispatched && previewAgentId
                ? `preview-${previewAgentId}`
                : lane.lane_id;
              const isCollapsedOrQueued = lane.collapsed || lane.status === 'queued';
              const expandedIndex = expandedOrdered.findIndex((item) => item.lane_id === lane.lane_id);
              const onCurrentPage = !needsPagination
                || (expandedIndex >= 0 && laneGridPageIndex(expandedIndex) === safeGridPage);
              const slotIndex = pageLanesOrdered.findIndex((item) => item.lane_id === lane.lane_id);
              const showInGrid = !isCollapsedOrQueued && onCurrentPage && slotIndex >= 0;
              const slotStyle = showInGrid
                ? expandedLaneSlot(slotIndex, layout)
                : LANE_KEEPALIVE_SLOT;

              return (
                <div
                  key={paneKey}
                  data-lane-id={lane.lane_id}
                  data-lane-collapsed={isCollapsedOrQueued || !onCurrentPage ? 'true' : 'false'}
                  data-lane-layout={layout}
                  aria-hidden={!showInGrid ? true : undefined}
                  style={slotStyle}
                  className={showInGrid ? shell : 'flex flex-col overflow-hidden'}
                >
                  <TerminalLanePane
                    lane={lane}
                    sessionRunId={sessionRunId}
                    workspaceVisible={visible}
                    gridVisible={showInGrid}
                    barFocused={barFocused}
                    configuredAgents={configuredAgents}
                    headerAgentName={!sessionDispatched ? previewAgentName ?? undefined : undefined}
                    attachIdentity={
                      !sessionDispatched
                        ? previewAgentId ?? undefined
                        : lane.configured_agent_id ?? lane.lane_id
                    }
                    layoutTick={layoutTick}
                    layoutMode={layout}
                    onFocusLane={handleFocus}
                    onCollapseLane={handleCollapse}
                    paneRef={showInGrid ? registerPane : undefined}
                    onOpenWorkspaceFile={onOpenWorkspaceFile}
                  />
                </div>
              );
            })}
          </div>
          {collapsed.length > 0 ? (
            <TerminalLaneFloatRail lanes={collapsed} configuredAgents={configuredAgents} onExpand={handleExpand} />
          ) : null}
        </div>
        <HandoffLinkOverlay
          edges={handoffEdges}
          paneRefs={paneRefs}
          stageRef={stageRef}
          refTick={layoutTick}
          hoverEdge={handoffHover}
          onHoverEdge={setHandoffHover}
          onSendToBar={(text) => {
            window.dispatchEvent(new CustomEvent('orchestrator-fill-bar', { detail: { text } }));
          }}
        />
      </div>
    </div>
  );
};
