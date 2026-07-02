import React from 'react';
import { Maximize2 } from 'lucide-react';
import type { PtyLane } from '../../types';
import {
  laneHeaderAgentName,
  LANE_SHELL_CLASS,
  laneShellBorderClass,
} from '../../services/terminalOrchestraUtils';
import { resolveBrandLogoSrc } from '../../services/brandLogos';
import { useLanguage } from '../LanguageContext';

interface TerminalLaneFloatRailProps {
  lanes: PtyLane[];
  configuredAgents: Array<{ name: string; agentType?: string }>;
  onExpand: (laneId: string) => void;
  className?: string;
}

export const TerminalLaneFloatRail: React.FC<TerminalLaneFloatRailProps> = ({
  lanes,
  configuredAgents,
  onExpand,
  className = '',
}) => {
  const { t } = useLanguage();
  if (lanes.length === 0) return null;

  return (
    <aside
      data-testid="terminal-float-rail"
      className={`w-[152px] shrink-0 flex flex-col justify-end gap-1.5 pb-0.5 ${className}`}
      aria-label={t('Collapsed lanes')}
    >
      {lanes.map((lane) => {
        const logo = resolveBrandLogoSrc({ agentType: lane.agent_type });
        const displayName = laneHeaderAgentName(lane, configuredAgents);
        return (
          <button
            key={lane.lane_id}
            type="button"
            data-testid={`float-lane-${lane.lane_id}`}
            onClick={() => onExpand(lane.lane_id)}
            className={`flex items-center gap-2 px-2.5 py-2 text-left transition-colors ${LANE_SHELL_CLASS} ${laneShellBorderClass(false)} hover:border-neutral-600`}
          >
            <span className="w-6 h-6 rounded-lg shrink-0 flex items-center justify-center overflow-hidden bg-neutral-900">
              {logo ? (
                <img src={logo} alt="" className="w-4 h-4 object-contain" />
              ) : (
                <span className="text-[9px] font-bold text-neutral-400">
                  {displayName.slice(0, 1)}
                </span>
              )}
            </span>
            <span className="text-[10px] font-medium text-neutral-200 truncate flex-1 min-w-0">
              {displayName}
            </span>
            <Maximize2 className="w-3 h-3 text-neutral-500 shrink-0" />
          </button>
        );
      })}
    </aside>
  );
};
