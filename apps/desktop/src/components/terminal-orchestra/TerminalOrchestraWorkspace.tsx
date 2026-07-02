import React from 'react';
import type { ClutchRunStatus } from '../../types';
import { useClutchState } from '../../services/clutchState';
import { TerminalLaneGrid } from './TerminalLaneGrid';

interface TerminalOrchestraWorkspaceProps {
  visible: boolean;
  clutchStatus: ClutchRunStatus;
  cliTool: string;
  sessionRunId: string;
  barFocused: boolean;
}

export const TerminalOrchestraWorkspace: React.FC<TerminalOrchestraWorkspaceProps> = ({
  visible,
  clutchStatus,
  cliTool,
  sessionRunId,
  barFocused,
}) => {
  const { state } = useClutchState();
  const lanes = state.pty_lanes ?? [];
  const dispatchEdges = state.dispatch_edges ?? [];

  return (
    <div data-testid="terminal-orchestra-workspace" className={visible ? 'block' : 'hidden'}>
      <TerminalLaneGrid
        lanes={lanes}
        dispatchEdges={dispatchEdges}
        sessionRunId={sessionRunId}
        visible={visible}
        barFocused={barFocused}
        defaultCliTool={cliTool}
      />
      <span className="sr-only">{clutchStatus}</span>
    </div>
  );
};
