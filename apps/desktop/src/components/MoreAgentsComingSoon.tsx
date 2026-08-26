import React, { useEffect, useState } from 'react';
import { useLanguage } from './LanguageContext';
import { COMING_SOON_AGENT_TABS, getAgentCapabilityTier } from '../services/agentCapabilityTiers';
import { resolveBrandLogoSrc } from '../services/brandLogos';
import { LegacyIcon } from './ui/LegacyIcon';
import { AgentCliCapabilityPreview } from './AgentCliCapabilityPreview';
import { fetchCliModelsConfig, type CliModelsScan } from '../services/cliConfigApi';
import type { AgentTypeId } from '../services/agentTypes';
import { BTN_GHOST } from './ui/buttonStyles';

type ScanKind = 'models' | 'skills' | 'mcp';

function CliModelsScanPreview({ agentType }: { agentType: AgentTypeId }) {
  const { t } = useLanguage();
  const [payload, setPayload] = useState<CliModelsScan | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchCliModelsConfig(agentType)
      .then((next) => {
        if (!cancelled) setPayload(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : t('Scan failed'));
      });
    return () => {
      cancelled = true;
    };
  }, [agentType, t]);

  const models = payload?.available_models ?? payload?.catalog ?? [];
  return (
    <div className="space-y-2" data-testid={`cli-models-scan-${agentType}`}>
      {error ? <p className="text-xs text-rose-700">{error}</p> : null}
      {!error && models.length === 0 ? (
        <p className="text-xs text-neutral-500">{t('No local config found')}</p>
      ) : (
        <ul className="space-y-1">
          {models.map((item) => (
            <li key={`${item.provider}:${item.model_id}`} className="text-xs font-mono">
              {item.name || item.model_id}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export const MoreAgentsComingSoon: React.FC<{ kind?: ScanKind }> = ({ kind = 'skills' }) => {
  const { t } = useLanguage();
  const [scanType, setScanType] = useState<AgentTypeId | null>(null);

  if (scanType && getAgentCapabilityTier(scanType) === 'readOnlyScan') {
    return (
      <div className="space-y-3 text-left">
        <button type="button" className={`${BTN_GHOST} text-xs`} onClick={() => setScanType(null)}>
          {t('Back')}
        </button>
        {kind === 'models' ? (
          <CliModelsScanPreview agentType={scanType} />
        ) : (
          <AgentCliCapabilityPreview agentType={scanType} kind={kind} />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4 text-left">
      <section className="space-y-2">
        <h3 className="text-[11px] font-bold uppercase tracking-wide text-neutral-600">{t('More agents')}</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {COMING_SOON_AGENT_TABS.map((item) => {
            const logo = resolveBrandLogoSrc({ agentType: item.agentType });
            const ready = getAgentCapabilityTier(item.agentType) === 'readOnlyScan';
            return (
              <button
                key={item.id}
                type="button"
                data-testid={`cli-scan-${item.agentType}`}
                disabled={!ready}
                onClick={() => ready && setScanType(item.agentType)}
                className={`flex items-center gap-2 p-3 rounded-xl border text-left ${
                  ready
                    ? 'border-neutral-200 bg-white hover:border-neutral-400'
                    : 'border-dashed border-neutral-200 bg-white/80 opacity-70'
                }`}
              >
                {logo ? (
                  <img src={logo} alt="" className="w-4 h-4 object-contain rounded-sm" />
                ) : (
                  <LegacyIcon name="smart_toy" className="w-4 h-4 text-neutral-400" />
                )}
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-neutral-700">{t(item.labelKey)}</div>
                  <div className="text-[10px] text-neutral-400">
                    {ready ? t('Scan local config') : t('Under development')}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
};
