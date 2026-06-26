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
import { BTN_FOCUS } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';

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
}) => {
  const { t } = useLanguage();

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

              {isMultiAgent && (
                <button
                  data-testid="settings-nav-workflows"
                  onClick={() => setView('workflows')}
                  className={`${navBtnBase} ${currentView === 'workflows' ? navBtnActive : navBtnIdle}`}
                >
                  <LegacyIcon
                    name="account_tree"
                    className={`text-[16px] ${currentView === 'workflows' ? 'opacity-100' : 'opacity-60'}`}
                  />
                  <span className="text-xs">{t("Workflows SOP")}</span>
                </button>
              )}

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
