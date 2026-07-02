import React from 'react';
import { Maximize2 } from 'lucide-react';
import type { PtyLane } from '../../types';
import { agentDisplayName } from '../../services/terminalOrchestraUtils';
import { resolveBrandLogoSrc } from '../../services/brandLogos';
import { useLanguage } from '../LanguageContext';

interface TerminalLaneFloatRailProps {
  lanes: PtyLane[];
  onExpand: (laneId: string) => void;
}

export const TerminalLaneFloatRail: React.FC<TerminalLaneFloatRailProps> = ({ lanes, onExpand }) => {
  const { t } = useLanguage();
  if (lanes.length === 0) return null;

  return (
    <aside
      data-testid="terminal-float-rail"
      className="w-[148px] shrink-0 flex flex-col gap-2 py-1"
      aria-label={t('Collapsed lanes')}
    >
      {lanes.map((lane) => {
        const logo = resolveBrandLogoSrc({ agentType: lane.agent_type });
        return (
        <button
          key={lane.lane_id}
          type="button"
          data-testid={`float-lane-${lane.lane_id}`}
          onClick={() => onExpand(lane.lane_id)}
          className="flex items-center gap-2 px-2.5 py-2 rounded-xl border border-outline-variant/40 bg-surface-container-low hover:bg-surface-container-high text-left transition-colors"
        >
          <span className="w-6 h-6 rounded-lg shrink-0 flex items-center justify-center overflow-hidden bg-surface-container-low">
            {logo ? (
              <img src={logo} alt="" className="w-4 h-4 object-contain" />
            ) : (
              <span className="text-[9px] font-bold text-on-surface-variant">
                {agentDisplayName(lane.agent_type).slice(0, 1)}
              </span>
            )}
          </span>
          <span className="text-[10px] font-medium text-on-surface truncate flex-1 min-w-0">
            {lane.label || agentDisplayName(lane.agent_type)}
          </span>
          <Maximize2 className="w-3 h-3 text-on-surface-variant shrink-0" />
        </button>
        );
      })}
    </aside>
  );
};
