import React, { Dispatch, SetStateAction } from 'react';
import { Agent, MainView } from '../types';
import { AgentManager } from './AgentManager';
import { WorkflowOrchestration } from './WorkflowOrchestration';
import AiToolsManager from './AiToolsManager';
import { SkillsRegistry } from './SkillsRegistry';
import { McpServerHub } from './McpServerHub';
import { ModelsManager } from './ModelsManager';
import { ThemeManager } from './ThemeManager';
import { useLanguage } from './LanguageContext';

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
  activeAgentId?: string | null;
  onActivateAgent?: (agent: Agent) => void;
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
  activeAgentId = null,
  onActivateAgent,
}) => {
  const { t } = useLanguage();

  const isModalOpen = ['agents', 'settings', 'workflows', 'tools', 'skills', 'mcp', 'models', 'appearance'].includes(currentView);

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
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                  currentView === 'settings'
                    ? 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs'
                    : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">settings</span>
                <span className="text-xs">{t("General")}</span>
              </button>

              <button
                data-testid="settings-nav-tools"
                onClick={() => setView('tools')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                  currentView === 'tools'
                    ? 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs'
                    : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">handyman</span>
                <span className="text-xs">{t("AI Tools")}</span>
              </button>

              <button
                data-testid="settings-nav-agents"
                onClick={() => setView('agents')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                  currentView === 'agents'
                    ? 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs'
                    : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">smart_toy</span>
                <span className="text-xs">{t("AI Agents")}</span>
              </button>

              {isMultiAgent && (
                <button
                  data-testid="settings-nav-workflows"
                  onClick={() => setView('workflows')}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left text-xs transition-all border ${
                    currentView === 'workflows'
                      ? 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs'
                      : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent'
                  }`}
                >
                  <span className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: currentView === 'workflows' ? "'FILL' 1" : undefined }}>
                    account_tree
                  </span>
                  <span className="text-xs">{t("Workflows SOP")}</span>
                </button>
              )}

              <button
                data-testid="settings-nav-models"
                onClick={() => setView('models')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                  currentView === 'models'
                    ? 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs'
                    : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">layers</span>
                <span className="text-xs">{t("Models Config")}</span>
              </button>

              <button
                data-testid="settings-nav-skills"
                onClick={() => setView('skills')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                  currentView === 'skills'
                    ? 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs'
                    : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">school</span>
                <span className="text-xs">{t("Skills Registry")}</span>
              </button>

              <button
                data-testid="settings-nav-mcp"
                onClick={() => setView('mcp')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                  currentView === 'mcp'
                    ? 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs'
                    : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">terminal</span>
                <span className="text-xs">{t("MCP Server Hub")}</span>
              </button>

              <button
                data-testid="settings-nav-appearance"
                onClick={() => setView('appearance')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-xs transition-all border ${
                  currentView === 'appearance'
                    ? 'bg-surface-bright text-on-surface font-extrabold border-outline/40 shadow-2xs'
                    : 'text-on-surface-variant hover:bg-surface-container-high/60 hover:text-on-surface border-transparent'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">palette</span>
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
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-10 text-center select-none bg-surface-bright text-on-surface">
                <span className="material-symbols-outlined text-[32px] text-on-surface-variant/40 font-variation-light mb-2">construction</span>
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
          <span className="material-symbols-outlined text-[15px] group-hover:rotate-90 transition-transform">
            close
          </span>
        </button>
      </div>
    </div>
  );
};
