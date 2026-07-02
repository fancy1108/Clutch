import React, { useCallback, useMemo, useRef, useState } from 'react';
import type { DispatchEdge, PtyLane } from '../../types';
import { clutchStore } from '../../services/clutchState';
import {
  agentDisplayName,
  collapsedLanes,
  computeLaneLayout,
  expandedLanes,
  laneStatusSummary,
} from '../../services/terminalOrchestraUtils';
import { TerminalLanePane } from './TerminalLanePane';
import { TerminalLaneFloatRail } from './TerminalLaneFloatRail';
import { HandoffLinkOverlay } from './HandoffLinkOverlay';

interface TerminalLaneGridProps {
  lanes: PtyLane[];
  dispatchEdges: DispatchEdge[];
  sessionRunId: string;
  visible: boolean;
  barFocused: boolean;
  defaultCliTool: string;
}

export const TerminalLaneGrid: React.FC<TerminalLaneGridProps> = ({
  lanes,
  dispatchEdges,
  sessionRunId,
  visible,
  barFocused,
  defaultCliTool,
}) => {
  const paneRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const stageRef = useRef<HTMLDivElement>(null);
  const [handoffHover, setHandoffHover] = useState<DispatchEdge | null>(null);
  const [refTick, setRefTick] = useState(0);

  const effectiveLanes = useMemo(() => {
    if (lanes.length > 0) return lanes;
    return [
      {
        lane_id: 'lane_primary',
        agent_type: defaultCliTool,
        label: 'Primary',
        status: 'running' as const,
        focused: true,
        collapsed: false,
        run_id: sessionRunId,
      },
    ];
  }, [lanes, defaultCliTool, sessionRunId]);

  const expanded = expandedLanes(effectiveLanes);
  const collapsed = collapsedLanes(effectiveLanes);
  const layout = computeLaneLayout(expanded.length);
  const hasHandoffGap = dispatchEdges.length > 0;

  const registerPane = useCallback((el: HTMLDivElement | null, laneId: string) => {
    const existing = paneRefs.current.get(laneId);
    if (el) {
      if (existing === el) return;
      paneRefs.current.set(laneId, el);
    } else {
      if (!existing) return;
      paneRefs.current.delete(laneId);
    }
    setRefTick((n) => n + 1);
  }, []);

  const handleFocus = (laneId: string) => {
    void clutchStore.focusLane(laneId);
  };

  const handleCollapse = (laneId: string) => {
    void clutchStore.collapseLane(laneId, true);
  };

  const handleComplete = (laneId: string) => {
    void clutchStore.completeLane(laneId);
  };

  const handleExpand = (laneId: string) => {
    void clutchStore.collapseLane(laneId, false);
    void clutchStore.focusLane(laneId);
  };

  const gridClass =
    layout === 1
      ? 'grid-cols-1'
      : layout === 2
        ? `grid-cols-2 ${hasHandoffGap ? 'gap-[52px]' : 'gap-3'}`
        : `grid-cols-3 ${hasHandoffGap ? 'gap-4' : 'gap-3'}`;

  return (
    <div data-testid="terminal-lane-grid" className="w-full max-w-5xl mx-auto flex flex-col min-h-[280px]">
      <div className="flex items-center justify-between gap-3 mb-3 px-1">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
            Terminal console
          </p>
          <p className="text-[11px] text-on-surface-variant/80 truncate mt-0.5">
            {laneStatusSummary(effectiveLanes)}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-2 px-1">
        {effectiveLanes.map((lane) => (
          <button
            key={lane.lane_id}
            type="button"
            data-testid={`lane-tab-${lane.lane_id}`}
            onClick={() => handleFocus(lane.lane_id)}
            className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold border transition-colors ${
              lane.focused
                ? 'bg-neutral-900 text-white border-neutral-900'
                : 'bg-surface-container-low text-on-surface-variant border-outline-variant/40 hover:bg-surface-container-high'
            }`}
          >
            {agentDisplayName(lane.agent_type)}
            {lane.collapsed ? ' · …' : ''}
          </button>
        ))}
      </div>

      <div ref={stageRef} className="relative flex-1 min-h-[280px]">
        <div className="flex gap-2 min-h-[280px]">
          <div className={`flex-1 grid ${gridClass} min-h-[280px] auto-rows-fr`}>
            {expanded.map((lane) => (
              <TerminalLanePane
                key={lane.lane_id}
                lane={lane}
                sessionRunId={sessionRunId}
                visible={visible}
                barFocused={barFocused}
                onFocusLane={handleFocus}
                onCollapseLane={handleCollapse}
                onCompleteLane={handleComplete}
                paneRef={registerPane}
              />
            ))}
          </div>
          {collapsed.length > 0 ? (
            <TerminalLaneFloatRail lanes={collapsed} onExpand={handleExpand} />
          ) : null}
        </div>
        <HandoffLinkOverlay
          edges={dispatchEdges}
          paneRefs={paneRefs.current}
          stageRef={stageRef}
          refTick={refTick}
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
