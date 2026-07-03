import React from 'react';
import type { ClutchRunStatus } from '../../types';
import { useClutchState } from '../../services/clutchState';
import { TerminalLaneGrid } from './TerminalLaneGrid';
import { TerminalSessionStatsBar } from './TerminalSessionStatsBar';
import { XTERM_KEEPALIVE_STYLE } from './terminalLaneLayout';

interface TerminalOrchestraWorkspaceProps {
  visible: boolean;
  clutchStatus: ClutchRunStatus;
  sessionRunId: string;
  barFocused: boolean;
  configuredAgents: Array<{ name: string; agentType?: string }>;
  sessionDispatched?: boolean;
  previewAgentType?: string | null;
  previewAgentId?: string | null;
  previewAgentName?: string | null;
  /** Changes when sidebars, dock, or panel toggles shift available terminal area. */
  layoutChromeKey?: string;
  /** Outer terminal container — observed for resize when chrome padding animates. */
  layoutObserveRef?: React.RefObject<HTMLElement | null>;
}

export const TerminalOrchestraWorkspace: React.FC<TerminalOrchestraWorkspaceProps> = ({
  visible,
  clutchStatus,
  sessionRunId,
  barFocused,
  configuredAgents,
  sessionDispatched = false,
  previewAgentType = null,
  previewAgentId = null,
  previewAgentName = null,
  layoutChromeKey = '',
  layoutObserveRef,
}) => {
  const { state } = useClutchState();
  const lanes = state.pty_lanes ?? [];
  const dispatchEdges = state.dispatch_edges ?? [];

  return (
    <div
      data-testid="terminal-orchestra-workspace"
      data-workspace-visible={visible ? 'true' : 'false'}
      className={visible ? 'flex flex-1 flex-col min-h-0 min-w-0' : 'flex flex-1 flex-col'}
      style={visible ? undefined : XTERM_KEEPALIVE_STYLE}
    >
      <TerminalLaneGrid
        lanes={lanes}
        dispatchEdges={dispatchEdges}
        sessionRunId={sessionRunId}
        visible={visible}
        barFocused={barFocused}
        configuredAgents={configuredAgents}
        sessionDispatched={sessionDispatched}
        previewAgentType={previewAgentType}
        previewAgentId={previewAgentId}
        previewAgentName={previewAgentName}
        layoutChromeKey={layoutChromeKey}
        layoutObserveRef={layoutObserveRef}
      />
      <div className="w-full shrink-0 mt-2">
        <TerminalSessionStatsBar
          sessionRunId={sessionRunId}
          visible={visible}
        />
      </div>
      <span className="sr-only">{clutchStatus}</span>
    </div>
  );
};
