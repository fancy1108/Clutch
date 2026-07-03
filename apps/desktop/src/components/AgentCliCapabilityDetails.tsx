import React, { useState } from 'react';
import { BTN_GHOST } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { useLanguage } from './LanguageContext';
import { agentTypeLabel, type AgentTypeId } from '../services/agentTypes';
import { AgentCliCapabilityPreview } from './AgentCliCapabilityPreview';

type AgentCliCapabilityDetailsProps = {
  agentType: AgentTypeId;
  kind: 'skills' | 'mcp';
};

export const AgentCliCapabilityDetails: React.FC<AgentCliCapabilityDetailsProps> = ({
  agentType,
  kind,
}) => {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  const label = agentTypeLabel(agentType);

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-neutral-500 leading-relaxed">
        {kind === 'skills'
          ? t('This agent uses native {label} skills bundled with the CLI — not Clutch Skills Registry bindings.').replace('{label}', label)
          : t('This agent uses native {label} MCP servers — not Clutch MCP Hub bindings.').replace('{label}', label)}
      </p>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={`${BTN_GHOST} text-[10px] inline-flex items-center gap-1`}
      >
        <LegacyIcon name={open ? 'expand_less' : 'expand_more'} className="text-[13px]" />
        {open ? t('Hide details') : t('View details')}
      </button>
      {open ? <AgentCliCapabilityPreview agentType={agentType} kind={kind} /> : null}
    </div>
  );
};
