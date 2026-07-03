import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchSkillsRegistry,
  mountSkillsDirectory,
  unmountSkillsDirectory,
  toggleSkillActive,
  notifySkillsUpdated,
  type ScannedSkill,
} from '../services/skillsApi';
import { SettingsPageHeader, SettingsPageShell } from './ui/SettingsPageHeader';
import { BTN_ICON_SM, BTN_GHOST, BTN_PRIMARY } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { ALERT_SUCCESS, ALERT_WARNING } from './ui/surfaceStyles';
import { useLanguage } from './LanguageContext';
import { AgentCapabilityTabs } from './AgentCapabilityTabs';
import { AgentCliCapabilityPreview } from './AgentCliCapabilityPreview';
import { MoreAgentsComingSoon } from './MoreAgentsComingSoon';
import { UnderDevelopmentNotice } from './ui/UnderDevelopmentNotice';
import type { AgentCapabilityTabId } from '../services/agentCapabilityTiers';
import { consumeSettingsAgentTab } from '../services/cliConfigApi';
import { pickSkillsDirectory, WorkspacePickerError } from '../services/pickSkillsDirectory';

export type { ScannedSkill };

export const SkillsRegistry: React.FC = () => {
  const { t } = useLanguage();
  const [scannedSkills, setScannedSkills] = useState<ScannedSkill[]>([]);
  const [mountedDirectories, setMountedDirectories] = useState<string[]>([]);
  const [newDirPath, setNewDirPath] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(true);
  const [capabilityTab, setCapabilityTab] = useState<AgentCapabilityTabId>('clutch');

  useEffect(() => {
    const stashed = consumeSettingsAgentTab();
    if (stashed) setCapabilityTab(stashed);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const data = await fetchSkillsRegistry();
      setMountedDirectories(data.mounted_directories);
      setScannedSkills(data.skills);
      notifySkillsUpdated();
    } catch {
      setErrorMsg(t('Sidecar unavailable — cannot load skills registry.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleToggleGlobalSkill = async (key: string) => {
    const skill = scannedSkills.find((item) => item.key === key);
    if (!skill) return;
    try {
      const data = await toggleSkillActive(key, !skill.isActiveGlobally);
      setScannedSkills(data.skills);
      notifySkillsUpdated();
    } catch {
      setErrorMsg(t('Failed to update skill — Sidecar may be offline.'));
    }
  };

  const handlePickDirectory = async () => {
    setErrorMsg('');
    try {
      const selected = await pickSkillsDirectory();
      if (selected) {
        setNewDirPath(selected);
      }
    } catch (err) {
      setErrorMsg(err instanceof WorkspacePickerError ? err.message : t('Could not open folder picker.'));
    }
  };

  const handleMountDirectory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDirPath.trim()) return;
    const path = newDirPath.trim();
    if (mountedDirectories.includes(path)) {
      setSuccessMsg(t('Directory is already mounted'));
      setTimeout(() => setSuccessMsg(''), 2000);
      return;
    }

    try {
      const data = await mountSkillsDirectory(path);
      setMountedDirectories(data.mounted_directories);
      setScannedSkills(data.skills);
      setNewDirPath('');
      const count = data.skills.length;
      setSuccessMsg(
        count > 0
          ? t('Mounted and discovered {count} skill(s).').replace('{count}', String(count))
          : t('Directory mounted. No SKILL.md files found yet.'),
      );
      notifySkillsUpdated();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Mount failed.');
    }
  };

  const handleUnmount = async (dir: string) => {
    try {
      const data = await unmountSkillsDirectory(dir);
      setMountedDirectories(data.mounted_directories);
      setScannedSkills(data.skills);
      notifySkillsUpdated();
    } catch {
      setErrorMsg('Failed to unmount directory.');
    }
  };

  return (
    <SettingsPageShell>
      <SettingsPageHeader
        isModalStyle
        icon="school"
        title={t('Global Skills Registry')}
        description={t('Clutch Skills Registry applies to the built-in agent. CLI tabs show native skill directories (read-only).')}
      />

        <AgentCapabilityTabs activeTab={capabilityTab} onTabChange={setCapabilityTab} />

        {capabilityTab === 'claude-cli' ? (
          <AgentCliCapabilityPreview agentType="claude-cli" kind="skills" />
        ) : null}
        {capabilityTab === 'opencode-cli' ? (
          <AgentCliCapabilityPreview agentType="opencode-cli" kind="skills" />
        ) : null}
        {capabilityTab === 'more' ? <MoreAgentsComingSoon /> : null}

        {capabilityTab === 'clutch' ? (
        <>
        <UnderDevelopmentNotice />

        {errorMsg && (
          <p className={ALERT_WARNING}>{errorMsg}</p>
        )}

        <div className="p-4 bg-neutral-50/50 border border-neutral-200/60 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">{t('Search Paths')}</h3>
              <p className="text-[9.5px]/snug text-neutral-400 font-sans">{t('Paths stored in Application Support and scanned on refresh.')}</p>
            </div>
            <button
              type="button"
              onClick={() => void refresh()}
              disabled={loading}
              className="text-[10px] font-bold text-neutral-500 hover:text-neutral-800 disabled:opacity-50"
            >
              {t('Rescan')}
            </button>
          </div>

          {loading ? (
            <p className="text-xs text-neutral-400 italic">{t('Loading skills registry…')}</p>
          ) : mountedDirectories.length === 0 ? (
            <p className="text-xs text-neutral-400 italic">{t('No skill directories mounted.')}</p>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              {mountedDirectories.map((dir) => (
                <div
                  key={dir}
                  className="flex items-center justify-between p-2.5 bg-white border border-neutral-200 rounded-lg text-xs"
                >
                  <div className="flex items-center gap-2.5 overflow-hidden">
                    <LegacyIcon name="folder_open" className="text-[16px] text-neutral-400" />
                    <span className="font-mono text-neutral-700 truncate">{dir}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleUnmount(dir)}
                    className={`${BTN_ICON_SM} text-neutral-400 hover:text-red-600 hover:bg-neutral-50`}
                    title={t('Unmount directory')}
                    aria-label={t('Unmount directory')}
                  >
                    <LegacyIcon name="delete" className="text-[15px] font-bold" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={(e) => void handleMountDirectory(e)} className="pt-2 border-t border-dashed border-neutral-200 space-y-2">
            <div className="flex flex-col sm:flex-row gap-2 sm:items-center">
              <button
                type="button"
                onClick={() => void handlePickDirectory()}
                className={`${BTN_GHOST} text-[10px] shrink-0 inline-flex items-center gap-1 self-start`}
              >
                <LegacyIcon name="folder_open" className="text-[13px]" />
                {t('Choose folder')}
              </button>
              <input
                type="text"
                value={newDirPath}
                onChange={(e) => setNewDirPath(e.target.value)}
                placeholder={t('e.g. ~/.cursor/skills')}
                className="flex-1 min-w-0 px-3 py-1.5 text-xs border border-neutral-200 bg-white focus:outline-none focus:border-neutral-900 rounded-lg font-mono placeholder:text-neutral-400"
              />
              <button
                type="submit"
                disabled={!newDirPath.trim()}
                className={`${BTN_PRIMARY} disabled:opacity-50 shrink-0 self-start sm:self-auto`}
              >
                {t('+ Mount Root')}
              </button>
            </div>
            <p className="text-[9.5px] text-neutral-400 leading-relaxed">
              {t('Hidden folders (e.g. ~/.cursor/skills): type the path directly, or press Cmd+Shift+. in the picker to show hidden files.')}
            </p>
          </form>

          {successMsg && (
            <p className={`${ALERT_SUCCESS} text-[10px] font-medium select-none`}>
              {successMsg}
            </p>
          )}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-[11px] font-extrabold text-[#111111] font-mono tracking-wider uppercase">{t('Discovered Skills')}</h3>
            <span className="text-[10px] text-neutral-400 font-semibold font-mono">{scannedSkills.length} {t('FOUND')}</span>
          </div>

          {scannedSkills.length === 0 ? (
            <p className="text-xs text-neutral-400 italic px-1">{t('No skills discovered yet.')}</p>
          ) : (
            <div className="border border-neutral-200/80 bg-white rounded-xl divide-y divide-neutral-100 overflow-hidden shadow-3xs">
              {scannedSkills.map(skill => (
                <div
                  key={skill.key}
                  className="p-3.5 flex items-start justify-between gap-4 hover:bg-neutral-50/20 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-neutral-800 font-mono">{skill.label}</span>
                      <span className="text-[8.5px] font-mono text-neutral-500 bg-neutral-100 px-1.5 py-0.2 rounded font-semibold">{skill.source}</span>
                    </div>
                    <p className="text-[11px] text-neutral-500 leading-relaxed font-normal">{skill.desc}</p>
                  </div>

                  <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                    <button
                      type="button"
                      onClick={() => void handleToggleGlobalSkill(skill.key)}
                      className={`w-9 h-5 rounded-full p-0.5 transition-all duration-300 relative cursor-pointer flex items-center ${
                        skill.isActiveGlobally ? 'bg-neutral-900 justify-end' : 'bg-neutral-200 justify-start'
                      }`}
                      title={t('Toggle global skill')}
                    >
                      <span className="w-4 h-4 rounded-full bg-white shadow-3xs block" />
                    </button>
                    {skill.isActiveGlobally ? (
                      <span className="text-[7.5px] uppercase font-mono text-emerald-700 font-extrabold bg-emerald-50 border border-emerald-150 px-1 py-0.5 rounded">{t('ACTIVE')}</span>
                    ) : (
                      <span className="text-[7.5px] uppercase font-mono text-neutral-400 bg-neutral-50 px-1 py-0.5 rounded border border-neutral-200/40">{t('Inactive')}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        </>
        ) : null}
    </SettingsPageShell>
  );
};
