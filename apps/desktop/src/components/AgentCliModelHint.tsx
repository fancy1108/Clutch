import React, { useCallback, useEffect, useState } from 'react';
import { useLanguage } from './LanguageContext';
import { agentTypeLabel, type AgentTypeId } from '../services/agentTypes';
import { openSettingsWithAgentTab, fetchCliModelsConfig } from '../services/cliConfigApi';
import { settingsTabForAgentType } from '../services/agentCapabilityTiers';
import { BTN_GHOST } from './ui/buttonStyles';

type AgentCliModelHintProps = {
  agentType: AgentTypeId;
};

export const AgentCliModelHint: React.FC<AgentCliModelHintProps> = ({ agentType }) => {
  const { t } = useLanguage();
  const [modelId, setModelId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const payload = await fetchCliModelsConfig(agentType);
      setModelId(payload.active_model_id);
    } catch {
      setModelId(null);
    } finally {
      setLoading(false);
    }
  }, [agentType]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const tab = settingsTabForAgentType(agentType);
  const label = agentTypeLabel(agentType);

  return (
    <div className="space-y-1">
      <label className="text-[10px] font-bold text-neutral-500 tracking-wider uppercase font-mono block">
        {t('Model')}
      </label>
      <div className="px-3 py-2 text-xs border border-neutral-200 bg-neutral-50 rounded-lg font-mono text-neutral-800">
        {loading ? t('Scanning…') : modelId ?? t('Not detected in native config')}
      </div>
      <p className="text-[9.5px] text-neutral-400 leading-relaxed">
        {t('{label} models are managed outside Clutch.').replace('{label}', label)}
      </p>
      {tab ? (
        <button
          type="button"
          onClick={() => openSettingsWithAgentTab('models', tab)}
          className={`${BTN_GHOST} text-[10px] mt-1`}
        >
          {t('Open Settings → Models ({label})').replace('{label}', label)}
        </button>
      ) : null}
    </div>
  );
};
