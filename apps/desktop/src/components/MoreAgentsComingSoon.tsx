import React from 'react';
import { useLanguage } from './LanguageContext';
import { COMING_SOON_AGENT_TABS } from '../services/agentCapabilityTiers';
import { resolveBrandLogoSrc } from '../services/brandLogos';
import { LegacyIcon } from './ui/LegacyIcon';

export const MoreAgentsComingSoon: React.FC = () => {
  const { t } = useLanguage();

  return (
    <div className="space-y-4 text-left">
      <div className="flex items-start gap-2 px-3 py-2.5 rounded-xl bg-neutral-50 border border-neutral-200 text-neutral-700">
        <LegacyIcon name="construction" className="text-[14px] shrink-0 mt-0.5 text-neutral-500" />
        <p className="text-xs leading-relaxed">
          {t('More agent integrations are under development. Claude Code and OpenCode are available today; others will appear here when ready.')}
        </p>
      </div>

      <section className="space-y-2">
        <h3 className="text-[11px] font-bold uppercase tracking-wide text-neutral-600">{t('Coming soon')}</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {COMING_SOON_AGENT_TABS.map((item) => {
            const logo = resolveBrandLogoSrc({ agentType: item.agentType });
            return (
              <div
                key={item.id}
                className="flex items-center gap-2 p-3 rounded-xl border border-dashed border-neutral-200 bg-white/80"
              >
                {logo ? (
                  <img src={logo} alt="" className="w-4 h-4 object-contain rounded-sm opacity-60" />
                ) : null}
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-neutral-500">{t(item.labelKey)}</div>
                  <div className="text-[10px] text-neutral-400">{t('Under development')}</div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
