import React, { Dispatch, SetStateAction, useEffect, useRef, useState } from 'react';
import { Agent, MainView } from '../types';
import { AgentManager } from './AgentManager';
import { WorkflowOrchestration } from './WorkflowOrchestration';
import AiToolsManager from './AiToolsManager';
import { SkillsRegistry } from './SkillsRegistry';
import { McpServerHub } from './McpServerHub';
import { ModelsManager } from './ModelsManager';
import { ThemeManager } from './ThemeManager';
import { useLanguage } from './LanguageContext';
import type { Language } from './LanguageContext';
import { BTN_FOCUS, BTN_PRIMARY, BTN_SECONDARY } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { SettingsPageHeader, SettingsPageShell } from './ui/SettingsPageHeader';
import { SettingsSelect } from './ui/SettingsSelect';
import { saveAvatarPreference } from '../services/themeApi';
import { fetchAllowNetwork, fetchCrossSessionMemory, fetchDefaultWorkspaceId, fetchHighRiskConfirm, fetchLocalTrust, fetchStrictSandbox, clearCrossSessionMemory, saveAllowNetwork, saveCrossSessionMemory, saveDefaultWorkspaceId, saveHighRiskConfirm, saveStrictSandbox, saveUntrustedConfirm } from '../services/permissionApi';
import { FONT_SIZE_LABEL_KEYS, FONT_SIZE_OPTIONS, type AppFontSize } from '../services/fontSizePreference';
import { fetchWorkspaces, type WorkspaceInfo } from '../services/workspaceApi';
import { SIDECAR_BASE as BASE, sidecarFetch } from '../services/sidecarUrl';
import { setUserChatAvatar } from '../services/clutchState';
import defaultAvatar from '../assets/default_avatar.jpg';

interface SystemPreferencesModalProps {
  currentView: MainView;
  setView: (view: MainView) => void;
  isMultiAgent: boolean;
  selectedModel: string;
  setSelectedModel: Dispatch<SetStateAction<string>>;
  activeModelId: string;
  setActiveModelId: Dispatch<SetStateAction<string>>;
  configuredModels: Array<{
    id: string;
    name: string;
    provider: string;
    providerId: string;
    contextWindow: string;
    temperature: number;
    sourceSummary: string;
    credentialSourceLabel: string | null;
  }>;
  setConfiguredModels: Dispatch<SetStateAction<Array<any>>>;
  themeId: string;
  setThemeId: (themeId: string) => void;
  workspaceLabel?: string | null;
  sessionActive?: boolean;
  onUseWorkflowInChat?: (workflowId: string, workflowName: string) => void;
  onSelectWorkflow?: (workflowId: string, workflowName: string) => void;
  onClearSelectedWorkflow?: () => void;
  selectedWorkflowId?: string | null;
  activeAgentId?: string | null;
  onActivateAgent?: (agent: Agent) => void;
  userAvatar: string;
  setUserAvatar: (avatar: string) => void;
  userName?: string;
  setUserName?: (name: string) => void;
  fontSize: AppFontSize;
  setFontSize: (fontSize: AppFontSize) => void;
  appVersion?: string;
  onApplyDefaultWorkspace?: (workspaceId: string) => void;
  onHighRiskConfirmChange?: (enabled: boolean) => void;
}

export const SystemPreferencesModal: React.FC<SystemPreferencesModalProps> = ({
  currentView,
  setView,
  isMultiAgent,
  selectedModel,
  setSelectedModel,
  activeModelId,
  setActiveModelId,
  configuredModels,
  setConfiguredModels,
  themeId,
  setThemeId,
  workspaceLabel,
  sessionActive = false,
  onUseWorkflowInChat,
  onSelectWorkflow,
  onClearSelectedWorkflow,
  selectedWorkflowId = null,
  activeAgentId = null,
  onActivateAgent,
  userAvatar,
  setUserAvatar,
  userName = 'User',
  setUserName,
  fontSize,
  setFontSize,
  appVersion = '',
  onApplyDefaultWorkspace,
  onHighRiskConfirmChange,
}) => {
  const { t, language, setLanguage } = useLanguage();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [strictSandbox, setStrictSandbox] = useState(false);
  const [strictSandboxLoading, setStrictSandboxLoading] = useState(true);
  const [allowNetwork, setAllowNetwork] = useState(false);
  const [allowNetworkLoading, setAllowNetworkLoading] = useState(true);
  const [crossSessionMemory, setCrossSessionMemory] = useState(false);
  const [memoryEntryCount, setMemoryEntryCount] = useState(0);
  const [crossSessionMemoryLoading, setCrossSessionMemoryLoading] = useState(true);
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [defaultWorkspaceId, setDefaultWorkspaceId] = useState('');
  const [highRiskConfirm, setHighRiskConfirm] = useState(true);
  const [highRiskConfirmLoading, setHighRiskConfirmLoading] = useState(true);
  const [untrustedConfirm, setUntrustedConfirm] = useState(true);
  const [memoryQuery, setMemoryQuery] = useState('');
  const [memoryHits, setMemoryHits] = useState<Array<{ rel: string; snippet: string; path: string }>>([]);
  const [eventWebhook, setEventWebhook] = useState('');
  const [eventEmail, setEventEmail] = useState('');

  useEffect(() => {
    let cancelled = false;
    void fetchStrictSandbox()
      .then((enabled) => {
        if (!cancelled) setStrictSandbox(enabled);
      })
      .catch(() => {
        if (!cancelled) setStrictSandbox(false);
      })
      .finally(() => {
        if (!cancelled) setStrictSandboxLoading(false);
      });
    void fetchAllowNetwork()
      .then((enabled) => {
        if (!cancelled) setAllowNetwork(enabled);
      })
      .catch(() => {
        if (!cancelled) setAllowNetwork(false);
      })
      .finally(() => {
        if (!cancelled) setAllowNetworkLoading(false);
      });
    void fetchCrossSessionMemory()
      .then((payload) => {
        if (!cancelled) {
          setCrossSessionMemory(payload.enabled);
          setMemoryEntryCount(payload.entries?.length ?? 0);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCrossSessionMemory(false);
          setMemoryEntryCount(0);
        }
      })
      .finally(() => {
        if (!cancelled) setCrossSessionMemoryLoading(false);
      });
    void fetchWorkspaces()
      .then((listed) => {
        if (!cancelled) setWorkspaces(listed.workspaces);
      })
      .catch(() => {
        if (!cancelled) setWorkspaces([]);
      });
    void fetchDefaultWorkspaceId()
      .then((id) => {
        if (!cancelled) setDefaultWorkspaceId(id);
      })
      .catch(() => {
        if (!cancelled) setDefaultWorkspaceId('');
      });
    void fetchHighRiskConfirm()
      .then((enabled) => {
        if (!cancelled) setHighRiskConfirm(enabled);
      })
      .catch(() => {
        if (!cancelled) setHighRiskConfirm(true);
      })
      .finally(() => {
        if (!cancelled) setHighRiskConfirmLoading(false);
      });
    void fetchLocalTrust()
      .then((trust) => {
        if (!cancelled) setUntrustedConfirm(trust.untrusted_confirm);
      })
      .catch(() => {
        if (!cancelled) setUntrustedConfirm(true);
      });
    void sidecarFetch(`${BASE}/api/preferences/event-channel`)
      .then(async (res) => {
        if (!res.ok || cancelled) return;
        const body = (await res.json()) as { webhook?: string; email?: string };
        setEventWebhook(body.webhook ?? '');
        setEventEmail(body.email ?? '');
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      alert(t("Supported formats: PNG, JPG, GIF. Max file size: 5MB."));
      return;
    }

    const reader = new FileReader();
    reader.onload = async (event) => {
      const base64 = event.target?.result as string;
      try {
        await saveAvatarPreference(base64);
        setUserAvatar(base64);
        setUserChatAvatar(base64);
      } catch (err) {
        console.error('Failed to save avatar:', err);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleResetAvatar = async () => {
    try {
      await saveAvatarPreference('');
      setUserAvatar('');
      setUserChatAvatar('');
    } catch (err) {
      console.error('Failed to reset avatar:', err);
    }
  };

  const isModalOpen = ['agents', 'settings', 'workflows', 'tools', 'skills', 'mcp', 'models', 'appearance'].includes(currentView);
  const navBtnBase = `w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-left text-[11px] transition-all border ${BTN_FOCUS}`;
  const navBtnActive = 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs';
  const navBtnIdle = 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent';

  if (!isModalOpen) return null;

  return (
    <div className="fixed inset-0 bg-neutral-900/10 backdrop-blur-xs flex items-center justify-center z-[100] animate-fade-in p-6 select-none leading-normal">
      {/* Click backdrop to close */}
      <div className="absolute inset-0" onClick={() => setView('chat')} />

      {/* Modal Body Container (Exactly 1040x640) */}
      <div 
        style={{ width: '1040px', height: '640px' }}
        className="bg-surface text-on-surface rounded-[24px] shadow-xl border border-outline/50 flex overflow-hidden relative z-10 transition-all duration-300 animate-scale-up"
      >
        
        {/* Modal Split View */}
        <div className="flex-1 flex overflow-hidden min-h-0 bg-surface-dim">
          
          {/* Modal Left Sidebar Selector */}
          <div className="w-[240px] bg-surface-container border-r border-outline flex flex-col p-6 justify-between flex-shrink-0">
            <div className="space-y-1.5 text-left">
              <p className="font-bold text-[10px] uppercase tracking-widest text-on-surface-variant mb-3.5 px-3">
                {t("System Preferences")}
              </p>
              
              <button
                data-testid="settings-nav-general"
                onClick={() => setView('settings')}
                className={`${navBtnBase} ${currentView === 'settings' ? navBtnActive : navBtnIdle}`}
              >
                <LegacyIcon name="settings" className="text-[16px]" />
                <span className="text-xs">{t("General")}</span>
              </button>

              <button
                data-testid="settings-nav-tools"
                onClick={() => setView('tools')}
                className={`${navBtnBase} ${currentView === 'tools' ? navBtnActive : navBtnIdle}`}
              >
                <LegacyIcon name="handyman" className="text-[16px]" />
                <span className="text-xs">{t("AI Tools")}</span>
              </button>

              <button
                data-testid="settings-nav-agents"
                onClick={() => setView('agents')}
                className={`${navBtnBase} ${currentView === 'agents' ? navBtnActive : navBtnIdle}`}
              >
                <LegacyIcon name="smart_toy" className="text-[16px]" />
                <span className="text-xs">{t("AI Agents")}</span>
              </button>

              <button
                data-testid="settings-nav-workflows"
                onClick={() => setView('workflows')}
                className={`${navBtnBase} ${currentView === 'workflows' ? navBtnActive : navBtnIdle}`}
              >
                <LegacyIcon
                  name="fork_right"
                  className={`text-[16px] ${currentView === 'workflows' ? 'opacity-100' : 'opacity-60'}`}
                />
                <span className="text-xs">{t("Workflows SOP")}</span>
              </button>

              <button
                data-testid="settings-nav-models"
                onClick={() => setView('models')}
                className={`${navBtnBase} ${currentView === 'models' ? navBtnActive : navBtnIdle}`}
              >
                <LegacyIcon name="layers" className="text-[16px]" />
                <span className="text-xs">{t("Models Config")}</span>
              </button>

              <button
                data-testid="settings-nav-skills"
                onClick={() => setView('skills')}
                className={`${navBtnBase} ${currentView === 'skills' ? navBtnActive : navBtnIdle}`}
              >
                <LegacyIcon name="school" className="text-[16px]" />
                <span className="text-xs">{t("Skills Registry")}</span>
              </button>

              <button
                data-testid="settings-nav-mcp"
                onClick={() => setView('mcp')}
                className={`${navBtnBase} ${currentView === 'mcp' ? navBtnActive : navBtnIdle}`}
              >
                <LegacyIcon name="terminal" className="text-[16px]" />
                <span className="text-xs">{t("MCP Server Hub")}</span>
              </button>

              <button
                data-testid="settings-nav-appearance"
                onClick={() => setView('appearance')}
                className={`${navBtnBase} ${currentView === 'appearance' ? navBtnActive : navBtnIdle}`}
              >
                <LegacyIcon name="palette" className="text-[16px]" />
                <span className="text-xs">{t("Appearance")}</span>
              </button>
            </div>

            <div className="space-y-2 select-none">
              <div className="bg-surface-container-high p-4 rounded-xl border border-outline/40 space-y-2 select-text">
                <p className="text-[9px] text-on-surface-variant font-mono font-bold uppercase tracking-wider text-left">{t("Status Overview")}</p>
                <div className="space-y-1 text-[10px] font-medium text-on-surface-variant text-left">
                  <div className="flex justify-between">
                    <span>{t("Workspace:")}</span>
                    <span className="font-semibold text-on-surface truncate max-w-[120px]" title={workspaceLabel ?? undefined}>
                      {workspaceLabel ?? '—'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>{t("Session:")}</span>
                    <span className={`font-mono font-bold ${sessionActive ? 'text-green-600' : 'text-on-surface-variant'}`}>
                      ● {sessionActive ? t("ACTIVE") : '—'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Modal Right Detail Panel */}
          <div className="flex-1 overflow-hidden flex flex-col bg-surface-bright text-on-surface">
            {currentView === 'agents' ? (
              <AgentManager
                isModalStyle={true}
                activeAgentId={activeAgentId}
                onActivateAgent={onActivateAgent}
              />
            ) : currentView === 'workflows' ? (
              <WorkflowOrchestration
                isModalStyle={true}
                onClose={() => setView('chat')}
                onUseInChat={onUseWorkflowInChat}
                onSelectWorkflow={onSelectWorkflow}
                onClearSelectedWorkflow={onClearSelectedWorkflow}
                selectedWorkflowId={selectedWorkflowId}
              />
            ) : currentView === 'tools' ? (
              <AiToolsManager isModalStyle={true} />
            ) : currentView === 'skills' ? (
              <SkillsRegistry />
            ) : currentView === 'mcp' ? (
              <McpServerHub />
            ) : currentView === 'models' ? (
              <ModelsManager 
                selectedModel={selectedModel}
                setSelectedModel={setSelectedModel}
                activeModelId={activeModelId}
                setActiveModelId={setActiveModelId}
                configuredModels={configuredModels}
                setConfiguredModels={setConfiguredModels}
              />
            ) : currentView === 'appearance' ? (
              <ThemeManager 
                currentThemeId={themeId}
                setThemeId={setThemeId}
              />
            ) : currentView === 'settings' ? (
              <SettingsPageShell>
                <SettingsPageHeader
                  isModalStyle
                  icon="settings"
                  title={t('General Settings')}
                  description={t('Customize your application profile, account settings and default preferences.')}
                />

                <div className="space-y-6">
                  {/* Avatar Settings Section */}
                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t("Profile Avatar")}
                    </h3>
                    <div className="flex items-center gap-6">
                      <div className="relative w-20 h-20 rounded-full overflow-hidden border border-outline/50 shadow-md bg-surface-container flex-shrink-0 flex items-center justify-center group">
                        <img 
                          className="w-full h-full object-cover" 
                          src={userAvatar || defaultAvatar} 
                          alt="User Avatar" 
                        />
                      </div>
                      
                      <div className="space-y-2.5">
                        <div className="flex gap-2">
                          <button
                            onClick={() => fileInputRef.current?.click()}
                            className={`${BTN_PRIMARY} px-3 py-1.5 text-xs font-semibold cursor-pointer flex items-center gap-1.5`}
                          >
                            <LegacyIcon name="upload" className="text-[14px]" />
                            {t("Choose Photo")}
                          </button>
                          
                          {userAvatar && (
                            <button
                              onClick={handleResetAvatar}
                              className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold cursor-pointer flex items-center gap-1.5`}
                            >
                              <LegacyIcon name="restart_alt" className="text-[14px]" />
                              {t("Reset to Default")}
                            </button>
                          )}
                        </div>
                        <p className="text-[10px] text-on-surface-variant/80">
                          {t("Supported formats: PNG, JPG, GIF. Max file size: 5MB.")}
                        </p>
                      </div>
                    </div>

                    <input
                      type="file"
                      ref={fileInputRef}
                      className="hidden"
                      accept="image/*"
                      onChange={handleFileChange}
                    />
                  </div>

                  {/* Profile Name Settings Section */}
                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t("Profile Name")}
                    </h3>
                    <div className="flex items-center gap-4 max-w-md">
                      <input
                        type="text"
                        value={userName}
                        onChange={(e) => setUserName?.(e.target.value)}
                        placeholder={t("Enter your name")}
                        className="flex-1 bg-surface border border-outline/40 rounded-xl px-4 py-2.5 text-xs text-on-surface focus:outline-none focus:border-primary/60 transition-colors"
                      />
                    </div>
                  </div>

                  {/* Font Size Settings Section */}
                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Font Size')}
                    </h3>
                    <div className="flex items-center gap-4 max-w-md">
                      <SettingsSelect
                        id="general-font-size"
                        value={fontSize}
                        options={FONT_SIZE_OPTIONS.map((option) => ({
                          value: option,
                          label: t(FONT_SIZE_LABEL_KEYS[option]),
                        }))}
                        onChange={(next) => setFontSize(next as AppFontSize)}
                      />
                    </div>
                  </div>

                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Default workspace')}
                    </h3>
                    <p className="text-[11px] text-on-surface-variant/80 max-w-xl">
                      {t('Open this project on launch. Last used workspace is kept when unset.')}
                    </p>
                    <div className="max-w-md">
                      <SettingsSelect
                        id="general-default-workspace"
                        value={defaultWorkspaceId}
                        options={[
                          { value: '', label: t('Last used workspace') },
                          ...workspaces.map((ws) => ({ value: ws.id, label: ws.name })),
                        ]}
                        onChange={(next) => {
                          setDefaultWorkspaceId(next);
                          void saveDefaultWorkspaceId(next)
                            .then(() => {
                              if (next) onApplyDefaultWorkspace?.(next);
                            })
                            .catch((err) => console.error('Failed to save default workspace:', err));
                        }}
                      />
                    </div>
                  </div>

                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Confirm before stopping a run')}
                    </h3>
                    <p className="text-[11px] text-on-surface-variant/80 max-w-xl">
                      {t('When on, Chat Stop asks once per session. Workflow Stop is never confirmed.')}
                    </p>
                    <button
                      type="button"
                      data-testid="high-risk-confirm-toggle"
                      disabled={highRiskConfirmLoading}
                      onClick={() => {
                        const next = !highRiskConfirm;
                        setHighRiskConfirm(next);
                        void saveHighRiskConfirm(next)
                          .then(() => onHighRiskConfirmChange?.(next))
                          .catch((err) => {
                          console.error('Failed to save high-risk confirm:', err);
                          setHighRiskConfirm(!next);
                        });
                      }}
                      className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold ${
                        highRiskConfirm ? 'border-primary/50 text-primary' : ''
                      }`}
                    >
                      {highRiskConfirm ? t('Confirm stop: On') : t('Confirm stop: Off')}
                    </button>
                  </div>

                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Confirm untrusted MCP and workflows')}
                    </h3>
                    <p className="text-[11px] text-on-surface-variant/80 max-w-xl">
                      {t('When on, enabling an MCP server or using a workflow in Chat asks once, then remembers trust.')}
                    </p>
                    <button
                      type="button"
                      data-testid="untrusted-confirm-toggle"
                      onClick={() => {
                        const next = !untrustedConfirm;
                        setUntrustedConfirm(next);
                        void saveUntrustedConfirm(next).catch((err) => {
                          console.error('Failed to save untrusted confirm:', err);
                          setUntrustedConfirm(!next);
                        });
                      }}
                      className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold ${
                        untrustedConfirm ? 'border-primary/50 text-primary' : ''
                      }`}
                    >
                      {untrustedConfirm ? t('Trust confirm: On') : t('Trust confirm: Off')}
                    </button>
                  </div>

                  {/* Strict sandbox (D21) */}
                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Strict sandbox')}
                    </h3>
                    <p className="text-[11px] text-on-surface-variant/80 max-w-xl">
                      {t('Reject shell commands and paths that escape the authorized workspace.')}
                    </p>
                    <button
                      type="button"
                      data-testid="strict-sandbox-toggle"
                      disabled={strictSandboxLoading}
                      onClick={() => {
                        const next = !strictSandbox;
                        setStrictSandbox(next);
                        void saveStrictSandbox(next).catch((err) => {
                          console.error('Failed to save strict sandbox:', err);
                          setStrictSandbox(!next);
                        });
                      }}
                      className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold ${
                        strictSandbox ? 'border-primary/50 text-primary' : ''
                      }`}
                    >
                      {strictSandbox ? t('Strict sandbox: On') : t('Strict sandbox: Off')}
                    </button>
                  </div>

                  {/* Allow network (D15) */}
                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Allow network')}
                    </h3>
                    <p className="text-[11px] text-on-surface-variant/80 max-w-xl">
                      {t('Enable the builtin web_search tool for Clutch Agent. On by default.')}
                    </p>
                    <button
                      type="button"
                      data-testid="allow-network-toggle"
                      disabled={allowNetworkLoading}
                      onClick={() => {
                        const next = !allowNetwork;
                        setAllowNetwork(next);
                        void saveAllowNetwork(next).catch((err) => {
                          console.error('Failed to save allow network:', err);
                          setAllowNetwork(!next);
                        });
                      }}
                      className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold ${
                        allowNetwork ? 'border-primary/50 text-primary' : ''
                      }`}
                    >
                      {allowNetwork ? t('Allow network: On') : t('Allow network: Off')}
                    </button>
                  </div>

                  {/* Cross-session memory (D16) */}
                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Cross-session memory')}
                    </h3>
                    <p className="text-[11px] text-on-surface-variant/80 max-w-xl">
                      {t('Let Clutch Agent remember preferences across Chat sessions. Project notes go to .clutch/memory/MEMORY.md (open in Files).')}
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        data-testid="cross-session-memory-toggle"
                        disabled={crossSessionMemoryLoading}
                        onClick={() => {
                          const next = !crossSessionMemory;
                          setCrossSessionMemory(next);
                          void saveCrossSessionMemory(next).catch((err) => {
                            console.error('Failed to save cross-session memory:', err);
                            setCrossSessionMemory(!next);
                          });
                        }}
                        className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold ${
                          crossSessionMemory ? 'border-primary/50 text-primary' : ''
                        }`}
                      >
                        {crossSessionMemory ? t('Memory: On') : t('Memory: Off')}
                      </button>
                      <button
                        type="button"
                        data-testid="clear-cross-session-memory"
                        disabled={memoryEntryCount === 0}
                        onClick={() => {
                          void clearCrossSessionMemory()
                            .then((n) => setMemoryEntryCount(Math.max(0, memoryEntryCount - n)))
                            .catch((err) => console.error('Failed to clear memory:', err));
                        }}
                        className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold`}
                      >
                        {t('Clear memory')} ({memoryEntryCount})
                      </button>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        data-testid="memory-search-input"
                        value={memoryQuery}
                        onChange={(e) => setMemoryQuery(e.target.value)}
                        placeholder={t('Search .clutch/memory')}
                        className="flex-1 min-w-[160px] bg-surface border border-outline/40 rounded-xl px-3 py-2 text-xs"
                      />
                      <button
                        type="button"
                        data-testid="memory-search-run"
                        className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold`}
                        onClick={() => {
                          void sidecarFetch(`${BASE}/api/memory/search?q=${encodeURIComponent(memoryQuery)}`)
                            .then(async (res) => {
                              if (!res.ok) return;
                              const body = (await res.json()) as { hits?: Array<{ rel: string; snippet: string; path: string }> };
                              setMemoryHits(body.hits ?? []);
                            })
                            .catch(() => setMemoryHits([]));
                        }}
                      >
                        {t('Search')}
                      </button>
                    </div>
                    <ul className="space-y-1">
                      {memoryHits.map((hit) => (
                        <li key={hit.path}>
                          <button
                            type="button"
                            data-testid="memory-search-hit"
                            className="w-full text-left text-[11px] rounded-lg border border-outline/30 px-3 py-2 hover:bg-surface"
                            onClick={() => {
                              window.dispatchEvent(new CustomEvent('clutch-open-file', { detail: { path: hit.rel } }));
                              setView('chat');
                            }}
                          >
                            <div className="font-mono truncate">{hit.rel}</div>
                            <div className="text-on-surface-variant truncate">{hit.snippet}</div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Event channel')}
                    </h3>
                    <p className="text-[11px] text-on-surface-variant/80 max-w-xl">
                      {t('Webhook or email for wake-up events. Test posts a Chat Continue banner.')}
                    </p>
                    <input
                      data-testid="event-channel-webhook"
                      value={eventWebhook}
                      onChange={(e) => setEventWebhook(e.target.value)}
                      placeholder="https://…"
                      className="w-full bg-surface border border-outline/40 rounded-xl px-3 py-2 text-xs"
                    />
                    <input
                      data-testid="event-channel-email"
                      value={eventEmail}
                      onChange={(e) => setEventEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full bg-surface border border-outline/40 rounded-xl px-3 py-2 text-xs"
                    />
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        data-testid="event-channel-save"
                        className={`${BTN_SECONDARY} px-3 py-1.5 text-xs font-semibold`}
                        onClick={() => {
                          void sidecarFetch(`${BASE}/api/preferences/event-channel`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ webhook: eventWebhook, email: eventEmail }),
                          });
                        }}
                      >
                        {t('Save')}
                      </button>
                      <button
                        type="button"
                        data-testid="event-channel-test"
                        className={`${BTN_PRIMARY} px-3 py-1.5 text-xs font-semibold`}
                        onClick={() => {
                          void sidecarFetch(`${BASE}/api/preferences/event-channel`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ webhook: eventWebhook, email: eventEmail }),
                          }).then(() =>
                            sidecarFetch(`${BASE}/api/event-channel/test`, { method: 'POST' }).then(async (res) => {
                              if (!res.ok) return;
                              const body = (await res.json()) as { event?: { title?: string; message?: string } };
                              window.dispatchEvent(new CustomEvent('clutch-event-channel', { detail: body.event }));
                            }),
                          );
                        }}
                      >
                        {t('Test event')}
                      </button>
                    </div>
                  </div>

                  {/* Language Settings Section */}
                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Language')}
                    </h3>
                    <div
                      className="inline-flex items-center bg-surface p-1 rounded-lg border border-outline/40"
                      data-testid="settings-language-toggle"
                    >
                      <button
                        type="button"
                        data-testid="lang-en"
                        onClick={() => setLanguage('en' as Language)}
                        className={`px-3 py-1.5 text-[11px] rounded-md transition-all cursor-pointer ${
                          language === 'en'
                            ? 'bg-surface-bright text-on-surface font-bold shadow-sm'
                            : 'text-on-surface-variant hover:text-on-surface font-medium'
                        }`}
                      >
                        English
                      </button>
                      <button
                        type="button"
                        data-testid="lang-zh"
                        onClick={() => setLanguage('zh' as Language)}
                        className={`px-3 py-1.5 text-[11px] rounded-md transition-all cursor-pointer ${
                          language === 'zh'
                            ? 'bg-surface-bright text-on-surface font-bold shadow-sm'
                            : 'text-on-surface-variant hover:text-on-surface font-medium'
                        }`}
                      >
                        中文
                      </button>
                    </div>
                  </div>

                  <div className="bg-surface-container/30 p-6 rounded-2xl border border-outline/30 space-y-2">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                      {t('Version')}
                    </h3>
                    <p data-testid="general-app-version" className="text-xs font-mono text-on-surface">
                      Clutch v{appVersion || '—'}
                    </p>
                  </div>
                </div>
              </SettingsPageShell>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-10 text-center select-none bg-surface-bright text-on-surface">
                <LegacyIcon name="construction" className="text-[32px] text-on-surface-variant/40 mb-2" />
                <p className="text-xs font-bold text-on-surface-variant">{t("Feature under active development")}</p>
              </div>
            )}
          </div>

        </div>

        {/* Floating Top-Right Close Button */}
        <button
          data-testid="settings-close"
          onClick={() => setView('chat')}
          className="absolute top-4 right-4 z-50 w-7 h-7 bg-surface-container/60 hover:bg-surface-container-high/60 text-on-surface-variant hover:text-on-surface rounded-full flex items-center justify-center transition-all group cursor-pointer border border-outline/30"
          title={t("Close Panel")}
        >
          <LegacyIcon name="close" className="text-[15px] group-hover:rotate-90 transition-transform" />
        </button>
      </div>
    </div>
  );
};
