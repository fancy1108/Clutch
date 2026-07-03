import React from 'react';
import { useLanguage } from './LanguageContext';
import { resolveBrandLogoSrc } from '../services/brandLogos';
import {
  AGENT_CAPABILITY_TABS,
  type AgentCapabilityTabId,
} from '../services/agentCapabilityTiers';

type AgentCapabilityTabsProps = {
  activeTab: AgentCapabilityTabId;
  onTabChange: (tab: AgentCapabilityTabId) => void;
  className?: string;
};

export const AgentCapabilityTabs: React.FC<AgentCapabilityTabsProps> = ({
  activeTab,
  onTabChange,
  className = '',
}) => {
  const { t } = useLanguage();

  return (
    <div className={`flex flex-wrap gap-1.5 ${className}`} role="tablist" aria-label={t('Agent capability tabs')}>
      {AGENT_CAPABILITY_TABS.map((tab) => {
        const logo = tab.id === 'more' ? null : resolveBrandLogoSrc({ agentType: tab.agentType });
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onTabChange(tab.id)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10.5px] font-semibold border transition-colors ${
              isActive
                ? 'bg-neutral-900 text-white border-neutral-900'
                : 'bg-white text-neutral-600 border-neutral-200 hover:bg-neutral-50 hover:text-neutral-900'
            }`}
          >
            {tab.id === 'more' ? (
              <span className="text-[11px] leading-none opacity-80">···</span>
            ) : logo ? (
              <img src={logo} alt="" className="w-3.5 h-3.5 object-contain rounded-sm" />
            ) : null}
            {t(tab.labelKey)}
          </button>
        );
      })}
    </div>
  );
};
