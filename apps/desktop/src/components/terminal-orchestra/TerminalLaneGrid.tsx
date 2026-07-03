import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { DispatchEdge, PtyLane } from '../../types';
import { clutchStore } from '../../services/clutchState';
import {
  buildPreviewPtyLane,
  collapsedLanes,
  computeLaneLayout,
  expandedLanes,
  orderLanesForGrid,
  uniqueLanesByLaneId,
} from '../../services/terminalOrchestraUtils';
import { TerminalLanePane } from './TerminalLanePane';
import { TerminalLaneFloatRail } from './TerminalLaneFloatRail';
import { HandoffLinkOverlay } from './HandoffLinkOverlay';
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
}) => {
  const paneRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const stageRef = useRef<HTMLDivElement>(null);
  const laneRowRef = useRef<HTMLDivElement>(null);
  const lastStageSizeRef = useRef<{ width: number; height: number } | null>(null);
  const [handoffHover, setHandoffHover] = useState<DispatchEdge | null>(null);
  const [layoutTick, setLayoutTick] = useState(0);

  const bumpLayoutTick = useCallback(() => {
    setLayoutTick((n) => n + 1);
  }, []);

  const scheduleLayoutRefit = useCallback(() => {
    return scheduleTerminalLayoutRefit(bumpLayoutTick);
  }, [bumpLayoutTick]);

  const displayLanes = useMemo(() => {
    if (sessionDispatched) {
      const candidates = lanes.filter((lane) => lane.status !== 'queued');
      return uniqueLanesByLaneId(candidates);
    }
    if (!previewAgentType) return [];
    return [buildPreviewPtyLane(previewAgentType, sessionRunId)];
  }, [lanes, previewAgentType, sessionRunId, sessionDispatched]);

  const handoffEdges = displayLanes.length >= 2 ? dispatchEdges : [];

  const expanded = expandedLanes(displayLanes);
  const collapsed = collapsedLanes(displayLanes);
  const layout = computeLaneLayout(Math.max(1, expanded.length));
  const expandedOrdered = orderLanesForGrid(
    expanded.length > 0 ? expanded : displayLanes,
    layout,
  );
  const laneLayoutKey = useMemo(
    () => [
      layout,
      displayLanes.map((lane) => `${lane.lane_id}:${lane.collapsed ? 1 : 0}:${lane.focused ? 1 : 0}`).join('|'),
    ].join('::'),
    [displayLanes, layout],
  );

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
    void clutchStore.collapseLane(laneId, true);
    scheduleLayoutRefit();
  };

  const handleExpand = (laneId: string) => {
    void clutchStore.collapseLane(laneId, false);
    void clutchStore.focusLane(laneId);
    scheduleLayoutRefit();
  };

  const shell = `${lanePaneOuterClass(false)} h-full w-full`;

  useEffect(() => {
    return scheduleLayoutRefit();
  }, [layoutChromeKey, scheduleLayoutRefit]);

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

  return (
    <div data-testid="terminal-lane-grid" className="w-full flex flex-1 flex-col min-h-0 min-w-0">
      <div ref={stageRef} className="relative flex flex-1 flex-col min-h-0 min-w-0">
        <div className="flex flex-1 gap-2 min-h-0 min-w-0">
          <div ref={laneRowRef} className="relative flex flex-1 min-h-0 min-w-0">
            {displayLanes.map((lane) => {
              const paneKey = !sessionDispatched && previewAgentId
                ? `preview-${previewAgentId}`
                : lane.lane_id;
              const isHidden = lane.collapsed || lane.status === 'queued';
              const slotIndex = expandedOrdered.findIndex((item) => item.lane_id === lane.lane_id);
              const slotStyle = isHidden
                ? LANE_KEEPALIVE_SLOT
                : expandedLaneSlot(slotIndex, layout);

              return (
                <div
                  key={paneKey}
                  data-lane-id={lane.lane_id}
                  data-lane-collapsed={isHidden ? 'true' : 'false'}
                  data-lane-layout={layout}
                  aria-hidden={isHidden ? true : undefined}
                  style={slotStyle}
                  className={isHidden ? 'flex flex-col overflow-hidden' : shell}
                >
                  <TerminalLanePane
                    lane={lane}
                    sessionRunId={sessionRunId}
                    visible={visible}
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
                    paneRef={isHidden ? undefined : registerPane}
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
