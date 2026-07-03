import React, { useCallback, useEffect, useState } from 'react';
import { BTN_GHOST } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { useLanguage } from './LanguageContext';
import { agentTypeLabel, type AgentTypeId } from '../services/agentTypes';
import {
  capabilityPageLabel,
  settingsTabForAgentType,
} from '../services/agentCapabilityTiers';
import {
  fetchCliMcpConfig,
  fetchCliSkillsConfig,
  openSettingsWithAgentTab,
  type CliMcpScanItem,
  type CliSkillScanItem,
} from '../services/cliConfigApi';
import type { MainView } from '../types';

type AgentCliCapabilityPreviewProps = {
  agentType: AgentTypeId;
  kind: 'skills' | 'mcp';
};

export const AgentCliCapabilityPreview: React.FC<AgentCliCapabilityPreviewProps> = ({
  agentType,
  kind,
}) => {
  const { t } = useLanguage();
  const [skills, setSkills] = useState<CliSkillScanItem[]>([]);
  const [servers, setServers] = useState<CliMcpScanItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const settingsView: MainView = kind === 'skills' ? 'skills' : 'mcp';
  const settingsTab = settingsTabForAgentType(agentType);
  const label = agentTypeLabel(agentType);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (kind === 'skills') {
        const payload = await fetchCliSkillsConfig(agentType);
        setSkills(payload.skills);
      } else {
        const payload = await fetchCliMcpConfig(agentType);
        setServers(payload.servers);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Scan failed'));
      setSkills([]);
      setServers([]);
    } finally {
      setLoading(false);
    }
  }, [agentType, kind, t]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const openSettings = () => {
    if (settingsTab) {
      openSettingsWithAgentTab(settingsView, settingsTab);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-[10px] text-neutral-500 leading-relaxed">
        {kind === 'skills'
          ? t('This agent uses {label} native skills — not the Clutch Skills Registry.').replace('{label}', label)
          : t('This agent uses {label} native MCP servers — not Clutch MCP Hub bindings.').replace('{label}', label)}
      </p>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className={`${BTN_GHOST} text-[10px] inline-flex items-center gap-1 disabled:opacity-50`}
        >
          <LegacyIcon name="sync" className={`text-[12px] ${loading ? 'animate-spin' : ''}`} />
          {t('Rescan')}
        </button>
        {settingsTab ? (
          <button type="button" onClick={openSettings} className={`${BTN_GHOST} text-[10px]`}>
            {capabilityPageLabel(settingsView, agentType)}
          </button>
        ) : null}
      </div>

      {error ? <p className="text-[10px] text-rose-700">{error}</p> : null}

      {kind === 'skills' ? (
        <div className="border border-neutral-200 bg-white rounded-xl p-3 min-h-64 max-h-96 overflow-y-auto space-y-2">
          {loading ? (
            <p className="text-[10px] text-neutral-400 italic">{t('Scanning skills…')}</p>
          ) : skills.length === 0 ? (
            <p className="text-[10px] text-neutral-400 italic">{t('No SKILL.md files found in native paths.')}</p>
          ) : (
            skills.map((skill) => (
              <div key={skill.key} className="text-[10px] border-b border-neutral-100 pb-2 last:border-0 last:pb-0">
                <div className="font-bold text-neutral-800">{skill.label}</div>
                <div className="text-neutral-500 mt-0.5 line-clamp-2">{skill.desc}</div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="border border-neutral-200 bg-white rounded-xl p-3 min-h-64 max-h-96 overflow-y-auto space-y-2">
          {loading ? (
            <p className="text-[10px] text-neutral-400 italic">{t('Scanning MCP servers…')}</p>
          ) : servers.length === 0 ? (
            <p className="text-[10px] text-neutral-400 italic leading-relaxed">
              {t('No MCP servers found in native config. Claude Code uses ~/.claude.json and project .mcp.json — Cursor MCP (~/.cursor/mcp.json) is separate.')}
            </p>
          ) : (
            servers.map((server) => (
              <div key={`${server.name}-${server.endpoint}`} className="text-[10px] border-b border-neutral-100 pb-2 last:border-0 last:pb-0">
                <div className="flex items-center gap-2">
                  <div className="font-bold text-neutral-800">{server.name}</div>
                  {server.enabled_for_agent === false ? (
                    <span className="text-[8px] uppercase font-mono text-amber-700 bg-amber-50 border border-amber-200 px-1 py-0.5 rounded">
                      {t('Disabled for this agent')}
                    </span>
                  ) : null}
                </div>
                <div className="text-neutral-500 font-mono mt-0.5 break-all">{server.endpoint}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
