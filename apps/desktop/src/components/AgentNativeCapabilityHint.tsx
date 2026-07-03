import React from 'react';
import { BTN_GHOST } from './ui/buttonStyles';
import { useLanguage } from './LanguageContext';
import { agentTypeLabel, type AgentTypeId } from '../services/agentTypes';
import {
  capabilityPageLabel,
  settingsTabForAgentType,
} from '../services/agentCapabilityTiers';
import { openSettingsWithAgentTab } from '../services/cliConfigApi';
import type { MainView } from '../types';

type AgentNativeCapabilityHintProps = {
  agentType: AgentTypeId;
  kind: 'skills' | 'mcp';
};

export const AgentNativeCapabilityHint: React.FC<AgentNativeCapabilityHintProps> = ({
  agentType,
  kind,
}) => {
  const { t } = useLanguage();
  const label = agentTypeLabel(agentType);
  const settingsView: MainView = kind === 'skills' ? 'skills' : 'mcp';
  const settingsTab = settingsTabForAgentType(agentType) ?? 'more';

  const openSettings = () => {
    openSettingsWithAgentTab(settingsView, settingsTab);
  };

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-neutral-500 leading-relaxed">
        {kind === 'skills'
          ? t('{label} uses built-in CLI skills. See the Skills Registry page for details.')
              .replace('{label}', label)
          : t('{label} uses built-in CLI MCP servers. See the MCP Server Hub page for details.')
              .replace('{label}', label)}
      </p>
      <button type="button" onClick={openSettings} className={`${BTN_GHOST} text-[10px]`}>
        {capabilityPageLabel(settingsView, agentType)}
      </button>
    </div>
  );
};
