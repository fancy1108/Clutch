import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './sidebar';
import { ChatFeed, configuredEngineToRuntimeLabel } from './components/ChatFeed';
import { DesignWorkspace } from './components/design/DesignWorkspace';
import { getDesignSession, type CodingHandoff } from './services/designApi';
import { RightPanel } from './components/RightPanel';
import { WorkflowOrchestration } from './components/WorkflowOrchestration';
import { AgentManager } from './components/AgentManager';
import AiToolsManager from './components/AiToolsManager';
import { SkillsRegistry } from './components/SkillsRegistry';
import { McpServerHub } from './components/McpServerHub';
import { ModelsManager } from './components/ModelsManager';
import { ThemeManager, THEME_PRESETS } from './components/ThemeManager';
import { SystemPreferencesModal } from './components/SystemPreferencesModal';
import { PromptModal } from './components/PromptModal';
import { AppErrorBoundary } from './components/AppErrorBoundary';
import { FooterFieldChevron, FooterFieldLabel, FooterFieldValue, FooterMenuAction, FooterMenuItem, FooterMenuPanel, FooterMenuSection, FOOTER_CHIP_BUTTON_CLASS, FOOTER_CHIP_CLASS, footerIdleHiddenClass } from './components/FooterMenu';
import { MainView, RightTab, ChatMessage, UncommittedFile, DiffLine, type Agent, type ClutchState, type AppWorkspaceMode, type ToolStep } from './types';
import { resolveChatTerminalSyncTarget } from './services/chatTerminalSync';
import { fetchAgents } from './services/agentApi';
import {
  BUILTIN_AGENT_ID,
  getAgentDisplayName,
  isBuiltinAgent,
  mergeAgentsWithBuiltin,
} from './services/builtinAgent';
import {
  fetchPreferences,
  saveFontSizePreference,
  saveThemePreference,
  saveUserNamePreference,
  type ThemePresetId,
} from './services/themeApi';
import { DEFAULT_FONT_SIZE, type AppFontSize } from './services/fontSizePreference';
import { isWindowsHost, useHostOs } from './platform/hostOs';
import { LanguageProvider, useLanguage } from './components/LanguageContext';
import { OnboardingWizard } from './components/onboarding/OnboardingWizard';
import { CONTENT_TOP_WITH_BANNER, SIDEBAR_COLLAPSED_WIDTH_PX, SIDEBAR_EXPANDED_WIDTH_PX, CHROME_PANEL_TOGGLE_TOP_CSS, CHROME_PANEL_TOGGLE_HALF_PX } from './constants/layout';
import { ChromeEdgeToggle } from './components/ui/ChromeEdgeToggle';
import { BrandLogo } from './components/BrandLogo';
import { clutchMarkUrl } from './assets/brand';
import { DevOnboardingToolsEmptyPreview } from './components/onboarding/DevOnboardingToolsEmptyPreview';
import { fetchOnboardingState } from './services/onboardingApi';
import { clutchStore, createSessionRunId, submitChatMessage, useClutchState, setUserChatAvatar, clearWorkflowForSession } from './services/clutchState';
import {
  fetchSessions,
  resolveSessionHistoryWorkspaceId,
  startWorkflowRun,
  fetchRunState,
  deleteSession,
  createSession,
  compactRun,
  type SessionRecord,
} from './services/runApi';
import type { SlashCommandId } from './services/slashCommands';
import { fetchShellSnapshots } from './services/shellSnapshotApi';
import { listWorkflowItems, loadWorkflowById } from './services/workflowApi';
import {
  findWorkflowStep,
  shouldRouteWorkflowRefine,
  isWorkflowSystemAgent,
  orderedWorkflowAgentSteps,
  resolveInProgressWorkflowStep,
  resolveWorkflowMentionAgentId,
  type WorkflowAgentStep,
} from './services/workflowAgentSteps';
import { isClutchAgentType, agentTypeFromAgent, agentTypeLabel, isCliAgentType } from './services/agentTypes';
import {
  filterAgentsForTerminalWorkspace,
  filterCliAgents,
  isTerminalCapableAgentType,
  loadWorkspaceViewMode,
  resolveDefaultTerminalAgent,
  saveWorkspaceViewMode,
  type WorkspaceViewMode,
} from './services/workspaceViewMode';
import { CLI_DISPLAY, formatInputMention, saveLastCliAgentId, sessionHasTerminalHistory, sessionHasPersistableContent, isArchivedTerminalHistoryView, normalizeTerminalSessionForResume, shouldConfirmLeavingTerminal, shouldConfirmLeavingTerminalForNewChat } from './services/terminalOrchestraUtils';
import { resolveAgentBrandLogo, resolveBrandLogoSrc } from './services/brandLogos';
import {
  activateWorkspace,
  addWorkspace,
  removeWorkspace,
  fetchWorkspaceFile,
  resolveWorkspaceFile,
  fetchWorkspaceTree,
  fetchWorkspaceGit,
  fetchWorkspaces,
  fetchRepositoryGroups,
  createRepositoryGroup,
  updateRepositoryGroup,
  deleteRepositoryGroup,
  type FileTreeNode,
  type RepositoryGroup,
  type WorkspaceInfo,
} from './services/workspaceApi';
import { isImageWorkspacePath, isLargePreviewContent } from './services/workspacePathLinks';
import {
  absoluteWorkspacePath,
  isHtmlWorkspacePath,
  openPathInSystem,
} from './services/openInSystem';
import { workspaceMediaUrl } from './services/sidecarUrl';
import { pickWorkspaceFolder } from './services/pickWorkspaceFolder';
import {
  fetchModelsConfig,
  mapModelConfigToUi,
  modelKindMenuSuffix,
  resolveDefaultTextModelId,
  saveModelsConfig,
} from './services/modelsApi';
import { fetchDefaultWorkspaceId, fetchHighRiskConfirm, fetchPermissionMode, savePermissionMode, type PermissionMode } from './services/permissionApi';
import { fetchSkillsRegistry, type ScannedSkill } from './services/skillsApi';
import { BTN_GHOST, BTN_PRIMARY } from './components/ui/buttonStyles';
import { LegacyIcon } from './components/ui/LegacyIcon';
import { isTauri } from '@tauri-apps/api/core';
import { getVersion } from '@tauri-apps/api/app';

type InFlightTurnContext = {
  agentId: string | null;
  agentName: string;
  modelId: string | null;
  modelName: string;
  engineHint: string;
};

function MainLayout() {
  const { t } = useLanguage();
  const hostOs = useHostOs();
  const isWindows = isWindowsHost(hostOs);
  const { state: clutchState } = useClutchState();
  const [appVersion, setAppVersion] = useState<string>('1.0.0');

  useEffect(() => {
    if (isTauri()) {
      getVersion()
        .then((v) => setAppVersion(v))
        .catch((err) => console.warn('[Clutch] Failed to fetch app version:', err));
    }
  }, []);

  const [sessionRunId, setSessionRunId] = useState(() => createSessionRunId());
  const [highlightedDispatchEntryId, setHighlightedDispatchEntryId] = useState<string | null>(null);
  const [highlightedLogIndex, setHighlightedLogIndex] = useState<number | null>(null);

  const [promptModal, setPromptModal] = useState<{
    isOpen: boolean;
    title: string;
    message?: string;
    hasInput?: boolean;
    placeholder?: string;
    defaultValue?: string;
    onConfirm: (value: string) => void;
  } | null>(null);

  const hydrateRunState = useCallback(async (runId: string) => {
    const { state } = await fetchRunState(runId);
    return state;
  }, []);

  const scheduleBackgroundHydrateForRun = useCallback(
    (runId: string) => {
      const snapshot = clutchStore.getSnapshot();
      if (snapshot.run_id !== runId || snapshot.status !== 'running') return;
      clutchStore.scheduleBackgroundHydrate(runId, hydrateRunState);
    },
    [hydrateRunState],
  );

  useEffect(() => {
    void clutchStore.connect(sessionRunId).then(() => {
      const snapshot = clutchStore.getSnapshot();
      if (snapshot.status === 'running') {
        clutchStore.scheduleBackgroundHydrate(sessionRunId, hydrateRunState);
      }
    });
  }, [sessionRunId, hydrateRunState]);

  const clutchStatus = clutchState.status;
  const isTurnInProgress = clutchStatus === 'running' || clutchStatus === 'awaiting_human';
  const inFlightTurnRef = useRef<InFlightTurnContext | null>(null);
  const [pendingFooterModelId, setPendingFooterModelId] = useState<string | null>(null);
  const chatMessages = clutchState.messages as ChatMessage[];
  const terminalLogs = clutchState.terminal_logs;

  // Navigation & Structure views
  const [currentView, setView] = useState<MainView>('chat');
  const [appMode, setAppMode] = useState<AppWorkspaceMode>('coding');
  const [currentFlowName, setCurrentFlowName] = useState<string>('');
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [workflowAgentSteps, setWorkflowAgentSteps] = useState<WorkflowAgentStep[]>([]);
  const [isMultiAgent, setIsMultiAgent] = useState<boolean>(true);
  const [themeId, setThemeIdState] = useState<ThemePresetId>('pristine-light');
  const [fontSize, setFontSizeState] = useState<AppFontSize>(DEFAULT_FONT_SIZE);
  const [userAvatar, setUserAvatarState] = useState<string>('');
  const [userName, setUserNameState] = useState<string>('User');

  useEffect(() => {
    void fetchPreferences()
      .then((prefs) => {
        setThemeIdState(prefs.active_theme_id);
        setFontSizeState(prefs.font_size ?? DEFAULT_FONT_SIZE);
        if (prefs.user_avatar) {
          setUserAvatarState(prefs.user_avatar);
          setUserChatAvatar(prefs.user_avatar);
        }
        if (prefs.user_name) {
          setUserNameState(prefs.user_name);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ view?: MainView }>).detail;
      if (detail?.view) {
        setView(detail.view);
      }
    };
    window.addEventListener('clutch-navigate-settings', handler);
    return () => window.removeEventListener('clutch-navigate-settings', handler);
  }, []);


  const setThemeId = (id: string) => {
    const preset = THEME_PRESETS.find((item) => item.id === id);
    if (!preset) return;
    setThemeIdState(preset.id as ThemePresetId);
    void saveThemePreference(preset.id as ThemePresetId).catch(() => {});
  };

  const setFontSize = (size: AppFontSize) => {
    setFontSizeState(size);
    void saveFontSizePreference(size).catch(() => {});
  };

  const setUserName = (name: string) => {
    setUserNameState(name);
    void saveUserNamePreference(name).catch(() => {});
  };

  // Active selected model state
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [activeModelId, setActiveModelId] = useState<string>('');
  const [configuredModels, setConfiguredModels] = useState<Array<{
    id: string;
    name: string;
    provider: string;
    providerId: string;
    modelKind?: 'chat' | 'image' | 'video';
    contextWindow: string;
    temperature: number;
    sourceSummary: string;
    credentialSourceLabel: string | null;
  }>>([]);

  // Column Collapsing states
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [rightPanelOpen, setRightPanelOpen] = useState<boolean>(true);

  // File Preview state
  const [previewFile, setPreviewFile] = useState<{
    name: string;
    content: string;
    plain?: boolean;
    mediaSrc?: string;
  } | null>(null);
  const [previewToast, setPreviewToast] = useState<string | null>(null);

  // Repository list folders state
  const [folders, setFolders] = useState<import('./types').RepositoryFolder[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [historySessionViewRunId, setHistorySessionViewRunId] = useState<string | null>(null);
  const [shellSnapshotRunIds, setShellSnapshotRunIds] = useState<ReadonlySet<string>>(() => new Set());
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [repositoryGroups, setRepositoryGroups] = useState<RepositoryGroup[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [workspaceFiles, setWorkspaceFiles] = useState<FileTreeNode[]>([]);
  const [workspacePickError, setWorkspacePickError] = useState<string | null>(null);
  const [highRiskConfirmed, setHighRiskConfirmed] = useState(false);
  const [highRiskConfirmEnabled, setHighRiskConfirmEnabled] = useState(true);

  useEffect(() => {
    void fetchHighRiskConfirm()
      .then(setHighRiskConfirmEnabled)
      .catch(() => setHighRiskConfirmEnabled(true));
  }, []);

  // Reset high-risk confirmation when switching sessions
  useEffect(() => {
    setHighRiskConfirmed(false);
  }, [sessionRunId]);
  const [branchMenuOpen, setBranchMenuOpen] = useState(false);
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [agentMenuOpen, setAgentMenuOpen] = useState(false);
  const [workflowMenuOpen, setWorkflowMenuOpen] = useState(false);
  const [footerWorkflows, setFooterWorkflows] = useState<Array<{ id: string; name: string }>>([]);

  const closeFooterMenus = useCallback(() => {
    setBranchMenuOpen(false);
    setModelMenuOpen(false);
    setAgentMenuOpen(false);
    setWorkflowMenuOpen(false);
  }, []);
  const [workspaceGit, setWorkspaceGit] = useState<{ branch: string | null; branches: string[] }>({
    branch: null,
    branches: [],
  });
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(
    () => localStorage.getItem('clutch_active_agent_id') || BUILTIN_AGENT_ID,
  );
  const [workspaceViewMode, setWorkspaceViewMode] = useState<WorkspaceViewMode>(() => loadWorkspaceViewMode());
  const [configuredAgents, setConfiguredAgents] = useState<Agent[]>([]);
  const [inputValue, setInputValue] = useState<string>('');

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (branchMenuOpen || modelMenuOpen || agentMenuOpen || workflowMenuOpen) {
        const target = e.target as HTMLElement;
        if (target.closest('[data-testid^="footer-"]')) {
          return;
        }
        closeFooterMenus();
      }
    };
    window.addEventListener('click', handleOutsideClick);
    return () => {
      window.removeEventListener('click', handleOutsideClick);
    };
  }, [branchMenuOpen, modelMenuOpen, agentMenuOpen, workflowMenuOpen, closeFooterMenus]);

  const refreshWorkspaceGit = useCallback(async () => {
    try {
      const info = await fetchWorkspaceGit();
      setWorkspaceGit({ branch: info.branch, branches: info.branches });
    } catch {
      setWorkspaceGit({ branch: null, branches: [] });
    }
  }, []);

  const refreshWorkspaceFiles = useCallback(async () => {
    try {
      const nodes = await fetchWorkspaceTree();
      setWorkspaceFiles(nodes);
    } catch {
      setWorkspaceFiles([]);
    }
  }, []);

  useEffect(() => {
    void fetchWorkspaces()
      .then(async (listed) => {
        let workspacesList = listed.workspaces;
        let activeId = listed.active_id;
        try {
          const defaultId = await fetchDefaultWorkspaceId();
          if (defaultId && workspacesList.some((item) => item.id === defaultId) && activeId !== defaultId) {
            const info = await activateWorkspace(defaultId);
            workspacesList = workspacesList.map((item) => (item.id === defaultId ? info : item));
            activeId = defaultId;
            setWorkspace(info);
          }
        } catch {
          /* keep last-active workspace */
        }
        setWorkspaces(workspacesList);
        setActiveWorkspaceId(activeId);
        const active = workspacesList.find((item) => item.id === activeId) ?? null;
        if (active && active.id === activeId) {
          setWorkspace(active);
        }
        if (active) {
          await refreshWorkspaceFiles();
          await refreshWorkspaceGit();
        }
      })
      .catch(() => {});
    void fetchRepositoryGroups()
      .then((listed) => setRepositoryGroups(listed.groups))
      .catch(() => {});
  }, []);

  const syncModelsConfig = useCallback(async () => {
    const config = await fetchModelsConfig();
    const mapped = mapModelConfigToUi(config);
    setConfiguredModels(mapped.models);
    setActiveModelId(mapped.activeModelId);
    const active = mapped.models.find((m) => m.id === mapped.activeModelId);
    setSelectedModel(active?.name ?? '');
    return mapped;
  }, []);

  useEffect(() => {
    void syncModelsConfig().catch(() => {});
  }, [syncModelsConfig]);

  const refreshConfiguredAgents = async () => {
    try {
      setConfiguredAgents(await fetchAgents());
    } catch {
      setConfiguredAgents(mergeAgentsWithBuiltin([]));
    }
  };

  const selectDefaultAgent = () => {
    setSelectedAgentId(BUILTIN_AGENT_ID);
    localStorage.setItem('clutch_active_agent_id', BUILTIN_AGENT_ID);
  };

  const clearWorkflowSelection = () => {
    setSelectedWorkflowId(null);
    setCurrentFlowName('');
    void clearWorkflowForSession(sessionRunId);
  };

  const handleSetIsMultiAgent = useCallback((multi: boolean) => {
    setIsMultiAgent(multi);
    if (!multi) {
      clearWorkflowSelection();
      if (!selectedAgentId) {
        selectDefaultAgent();
      }
      setView((current) => (current === 'workflows' ? 'chat' : current));
    }
  }, [selectedAgentId]);

  useEffect(() => {
    void refreshConfiguredAgents();
  }, [currentView]);

  useEffect(() => {
    if (configuredAgents.length === 0) return;
    const sessionAgentId = localStorage.getItem(`clutch_session_agent_${sessionRunId}`);
    if (sessionAgentId) {
      const validSessionAgent = configuredAgents.some((agent) => agent.id === sessionAgentId);
      if (validSessionAgent) {
        setSelectedAgentId(sessionAgentId);
        return;
      }
    }
    const storedId = localStorage.getItem('clutch_active_agent_id');
    const validStored = storedId && configuredAgents.some((agent) => agent.id === storedId);
    if (validStored) {
      setSelectedAgentId(storedId);
      return;
    }
    const hasWorkflow = Boolean(selectedWorkflowId || clutchState.workflow_id);
    if (!hasWorkflow) {
      selectDefaultAgent();
    }
  }, [configuredAgents, selectedWorkflowId, clutchState.workflow_id, sessionRunId]);

  useEffect(() => {
    if (!isMultiAgent) {
      if (!selectedAgentId) selectDefaultAgent();
      return;
    }
    const hasWorkflow = Boolean(selectedWorkflowId || clutchState.workflow_id);
    if (!hasWorkflow && !selectedAgentId) selectDefaultAgent();
  }, [isMultiAgent, selectedWorkflowId, selectedAgentId, clutchState.workflow_id]);

  // Persist session-specific preferences
  useEffect(() => {
    if (!sessionRunId) return;
    localStorage.setItem(`clutch_session_mode_${sessionRunId}`, isMultiAgent ? 'multi' : 'single');
    localStorage.setItem(`clutch_session_flow_${sessionRunId}`, selectedWorkflowId || '');
    localStorage.setItem(`clutch_session_agent_${sessionRunId}`, selectedAgentId || '');
  }, [sessionRunId, isMultiAgent, selectedWorkflowId, selectedAgentId]);

  const handleActivateAgent = (agent: Agent) => {
    setSelectedAgentId(agent.id);
    localStorage.setItem('clutch_active_agent_id', agent.id);
    if (isCliAgentType(agentTypeFromAgent(agent))) {
      saveLastCliAgentId(agent.id);
    }
    if (isMultiAgent) clearWorkflowSelection();
    setInputValue(formatInputMention(getAgentDisplayName(agent)));
  };

  const cliAgents = useMemo(
    () => filterCliAgents(configuredAgents),
    [configuredAgents],
  );
  const hasCliAgents = cliAgents.length > 0;

  const activateTerminalSession = useCallback(() => {
    const agent = resolveDefaultTerminalAgent(configuredAgents);
    if (!agent) return;
    setSelectedAgentId(agent.id);
    localStorage.setItem('clutch_active_agent_id', agent.id);
    saveLastCliAgentId(agent.id);
    setInputValue(formatInputMention(getAgentDisplayName(agent)));
  }, [configuredAgents]);

  const leaveTerminalSession = useCallback(async () => {
    await clutchStore.closeAllPtySessions();
    await clutchStore.detachInteractivePty();
  }, []);

  const promptLeaveTerminal = useCallback((onProceed: () => void) => {
    setPromptModal({
      isOpen: true,
      title: t('Leave terminal mode?'),
      message: t(
        'Leaving terminal mode will end the current session and keep only handoff and dispatch records. Continue?',
      ),
      hasInput: false,
      onConfirm: () => {
        setPromptModal(null);
        void (async () => {
          await leaveTerminalSession();
          onProceed();
        })();
      },
    });
  }, [leaveTerminalSession, t]);

  const handleWorkspaceViewModeChange = useCallback((mode: WorkspaceViewMode) => {
    setWorkspaceViewMode(mode);
    saveWorkspaceViewMode(mode);
    if (mode === 'terminal') {
      activateTerminalSession();
    }
  }, [activateTerminalSession]);

  /**
   * D51 — Chat tool step → right-rail Terminal audit (highlight matching `[CHAT] Step`).
   * Stay in Chat mode: do NOT flip the center workspace to interactive Terminal mode
   * (that shows "Connecting interactive CLI…" and is a different surface).
   */
  const handleViewToolStepInTerminal = useCallback((step: ToolStep) => {
    const target = resolveChatTerminalSyncTarget(step, clutchState);
    setRightPanelOpen(true);
    setRightTab('terminal');
    setHighlightedLogIndex(target.logIndex);
    setHighlightedDispatchEntryId(target.dispatchEntryId);
    // If the user is already in Terminal mode, focus the matching lane — never enter it from here.
    if (workspaceViewMode === 'terminal') {
      void clutchStore.focusLane(target.laneId);
    }
  }, [clutchState, workspaceViewMode]);

  const isPlainLlmFooterEarly = !selectedWorkflowId && !clutchState.workflow_id;

  const prevSessionRunIdForTerminalRef = useRef(sessionRunId);

  useEffect(() => {
    if (workspaceViewMode !== 'terminal' || !isPlainLlmFooterEarly || configuredAgents.length === 0) return;
    if (prevSessionRunIdForTerminalRef.current === sessionRunId) return;
    prevSessionRunIdForTerminalRef.current = sessionRunId;
    activateTerminalSession();
  }, [sessionRunId, workspaceViewMode, isPlainLlmFooterEarly, configuredAgents, activateTerminalSession]);

  const syncSelectedAgentFromMention = useCallback((agentId: string | null) => {
    if (!agentId) return;
    const agent = configuredAgents.find((item) => item.id === agentId);
    if (!agent) return;
    if (workspaceViewMode === 'terminal' && !isCliAgentType(agentTypeFromAgent(agent))) return;
    if (agent.id === selectedAgentId) return;
    setSelectedAgentId(agent.id);
    localStorage.setItem('clutch_active_agent_id', agent.id);
    if (isCliAgentType(agentTypeFromAgent(agent))) {
      saveLastCliAgentId(agent.id);
    }
  }, [configuredAgents, selectedAgentId, workspaceViewMode]);

  const selectedAgent = configuredAgents.find((agent) => agent.id === selectedAgentId);
  const selectedAgentName = getAgentDisplayName(selectedAgent);
  const isPlainLlmFooter = !selectedWorkflowId && !clutchState.workflow_id;
  // Terminal Orchestra hides Model/Agent/Workflow in Coding only. Design has no
  // Chat/Terminal toggle — never inherit a stuck `terminal` viewMode into Design.
  const hideFooterSessionControls =
    appMode !== 'design' && isPlainLlmFooter && workspaceViewMode === 'terminal';
  const footerSelectableAgents = useMemo((): Agent[] => (
    isPlainLlmFooter && workspaceViewMode === 'terminal'
      ? filterAgentsForTerminalWorkspace(configuredAgents, 'terminal', agentTypeFromAgent) as Agent[]
      : configuredAgents
  ), [configuredAgents, isPlainLlmFooter, workspaceViewMode]);
  const mentionableAgents = useMemo(
    () => footerSelectableAgents.map((agent) => {
      const agentType = agentTypeFromAgent(agent);
      return {
        id: agent.id,
        name: getAgentDisplayName(agent),
        logo: resolveAgentBrandLogo(agent),
        dispatchTarget: CLI_DISPLAY[agentType] ?? getAgentDisplayName(agent),
        agentType,
      };
    }),
    [footerSelectableAgents],
  );
  // Design sessions reuse currentFlowName for the canvas title — never treat it as a Workflow SOP.
  const activeWorkflowLabel =
    appMode === 'design'
      ? '—'
      : clutchState.workflow_id || selectedWorkflowId || '—';
  const hasWorkflowSelection = isMultiAgent && appMode !== 'design' && activeWorkflowLabel !== '—';
  const multiAgentFooterName = hasWorkflowSelection
    ? '—'
    : selectedAgentId
      ? selectedAgentName
      : '—';
  const showFooterModel =
    appMode === 'design' || (!hasWorkflowSelection && isClutchAgentType(selectedAgent));
  const agentBoundModelId =
    selectedAgent && !isBuiltinAgent(selectedAgent) && selectedAgent.modelId
      ? selectedAgent.modelId
      : undefined;
  const footerEffectiveModelId =
    appMode === 'design' ? activeModelId : agentBoundModelId || activeModelId;
  const footerEffectiveModelName =
    configuredModels.find((model) => model.id === footerEffectiveModelId)?.name
    || selectedModel
    || '—';
  const isWorkflowChat = Boolean(clutchState.workflow_id || selectedWorkflowId);
  const inProgressWorkflowStep = isWorkflowChat
    ? resolveInProgressWorkflowStep(workflowAgentSteps, chatMessages, {
      activeNodeId: clutchState.active_node_id,
      activeAgentName: clutchState.active_agent,
    })
    : null;
  const chatActiveAgentName = isWorkflowChat
    ? (
      inProgressWorkflowStep?.agentName
      || (!isWorkflowSystemAgent(clutchState.active_agent) ? clutchState.active_agent : '')
      || workflowAgentSteps[0]?.agentName
      || ''
    )
    : isTurnInProgress
      ? (clutchState.active_agent || inFlightTurnRef.current?.agentName || selectedAgentName)
      : selectedAgentName;
  const resolveAgentLogo = useCallback((agentName: string) => {
    const agent = configuredAgents.find(
      (item) => getAgentDisplayName(item) === agentName || item.name === agentName,
    );
    if (agent) return resolveAgentBrandLogo(agent);
    const step = findWorkflowStep(workflowAgentSteps, { activeAgentName: agentName })
      ?? workflowAgentSteps.find((item) => item.agentName === agentName);
    if (step?.toolId && step.toolId !== 'clutch') {
      return resolveBrandLogoSrc({ toolId: step.toolId });
    }
    return undefined;
  }, [configuredAgents, workflowAgentSteps]);
  const chatActiveAgentAvatar =
    resolveAgentLogo(chatActiveAgentName)
    ?? (inProgressWorkflowStep?.toolId && inProgressWorkflowStep.toolId !== 'clutch'
      ? resolveBrandLogoSrc({ toolId: inProgressWorkflowStep.toolId })
      : undefined);
  const customAgentEngineLabel =
    selectedAgent && !isClutchAgentType(selectedAgent)
      ? agentTypeLabel(agentTypeFromAgent(selectedAgent))
      : '';
  const runtimeEngineHint = customAgentEngineLabel
    ? configuredEngineToRuntimeLabel(customAgentEngineLabel)
    : selectedModel;
  const chatRuntimeEngineHint =
    isTurnInProgress && !isWorkflowChat && inFlightTurnRef.current?.engineHint
      ? inFlightTurnRef.current.engineHint
      : runtimeEngineHint;
  const chatLlmModelName =
    isTurnInProgress && !isWorkflowChat && inFlightTurnRef.current?.modelName
      ? inFlightTurnRef.current.modelName
      : selectedModel;

  const refreshSessions = useCallback(async (mode: AppWorkspaceMode = appMode) => {
    try {
      // Sidebar shows every project — never scope to activeWorkspaceId.
      const [runs, snapshots] = await Promise.all([
        fetchSessions(resolveSessionHistoryWorkspaceId({ allWorkspaces: true }), mode),
        fetchShellSnapshots().catch(() => []),
      ]);
      setSessions(runs);
      setShellSnapshotRunIds(new Set(snapshots.map((snap) => snap.run_id)));
    } catch (error: unknown) {
      console.warn('[Clutch] sessions unavailable:', error);
    }
  }, [appMode]);

  const upsertLocalSession = useCallback((
    runId: string,
    title: string,
    opts?: { status?: string; workflowId?: string; mode?: AppWorkspaceMode },
  ) => {
    if (!workspace) return;
    const mode = opts?.mode ?? appMode;
    const trimmedTitle = title.trim().slice(0, 80) || (mode === 'design' ? t('New Design') : t('New session'));
    const status = opts?.status ?? (mode === 'design' ? 'idle' : 'running');
    const workflowId = opts?.workflowId ?? clutchState.workflow_id ?? '';
    setSessions((prev) => {
      const now = new Date().toISOString();
      const index = prev.findIndex((session) => session.run_id === runId);
      if (index >= 0) {
        const updated: SessionRecord = {
          ...prev[index],
          title: trimmedTitle,
          status,
          mode,
          workflow_id: workflowId || prev[index].workflow_id,
          updated_at: now,
        };
        // Move to front so sidebar recent-first order is immediate (before refresh).
        return [updated, ...prev.filter((_, i) => i !== index)];
      }
      const record: SessionRecord = {
        run_id: runId,
        workspace_id: workspace.id,
        workspace_name: workspace.name,
        title: trimmedTitle,
        workflow_id: workflowId,
        mode,
        status,
        started_at: now,
        updated_at: now,
      };
      return [record, ...prev];
    });
  }, [workspace, clutchState.workflow_id, t, appMode]);

  const registerSessionAfterSend = useCallback((
    runId: string,
    title: string,
    opts?: { status?: string; workflowId?: string; mode?: AppWorkspaceMode },
  ) => {
    const mode = opts?.mode ?? 'coding';
    upsertLocalSession(runId, title, { ...opts, mode });
    void createSession({
      run_id: runId,
      title: title.trim().slice(0, 80) || (mode === 'design' ? t('New Design') : t('New session')),
      workflow_id: opts?.workflowId ?? clutchState.workflow_id ?? '',
      mode,
    }).catch((error) => {
      console.warn('[Clutch] session register failed:', error);
    });
    void refreshSessions(mode);
  }, [upsertLocalSession, clutchState.workflow_id, t, refreshSessions]);

  useEffect(() => {
    void refreshSessions(appMode);
  }, [clutchState.run_id, clutchState.status, appMode, refreshSessions]);

  // Keep sidebar spinner in sync with live run status (MCP approve path used to leave history at "running").
  useEffect(() => {
    const runId = clutchState.run_id;
    if (!runId) return;
    const mapped =
      clutchStatus === 'running' ||
      clutchStatus === 'awaiting_human' ||
      clutchStatus === 'refining'
        ? 'running'
        : clutchStatus === 'failed'
          ? 'failed'
          : 'idle';
    setSessions((prev) => {
      const index = prev.findIndex((session) => session.run_id === runId);
      if (index < 0 || prev[index].status === mapped) return prev;
      const next = [...prev];
      next[index] = { ...next[index], status: mapped };
      return next;
    });
  }, [clutchState.run_id, clutchStatus]);

  // Active Tab inside the right side panel (Overview, Files, Flow, Changes, Terminal)
  const [rightTab, setRightTab] = useState<RightTab>('overview');

  const prevClutchStatusRef = useRef(clutchStatus);

  useEffect(() => {
    if (!isTurnInProgress) {
      inFlightTurnRef.current = null;
    }
  }, [isTurnInProgress]);

  useEffect(() => {
    if (isTurnInProgress || !pendingFooterModelId) return;
    const modelId = pendingFooterModelId;
    setPendingFooterModelId(null);
    void (async () => {
      try {
        await saveModelsConfig({ active_model_id: modelId });
        await syncModelsConfig();
      } catch (error) {
        console.error('[Clutch] deferred model switch failed:', error);
        setWorkspacePickError(
          error instanceof Error ? error.message : t('Failed to switch model.'),
        );
        await syncModelsConfig().catch(() => {});
      }
    })();
  }, [isTurnInProgress, pendingFooterModelId, syncModelsConfig, t]);

  useEffect(() => {
    const prev = prevClutchStatusRef.current;
    prevClutchStatusRef.current = clutchStatus;
    if (prev !== 'running' || clutchStatus === 'running' || !workspace) return;
    void refreshWorkspaceFiles();
    void refreshSessions();
  }, [clutchStatus, workspace, refreshWorkspaceFiles]);

  useEffect(() => {
    if (rightTab !== 'files' || !workspace) return;
    void refreshWorkspaceFiles();
  }, [rightTab, workspace?.id, refreshWorkspaceFiles]);

  useEffect(() => {
    const handler = (event: Event) => {
      const data = (event as CustomEvent).detail as { path?: string; diff_lines?: DiffLine[] };
      if (!data.path) return;
      setUncommitted((prev) => [
        ...prev.filter((file) => file.name !== data.path),
        { name: data.path, status: 'M', diffs: data.diff_lines || [], active: true },
      ]);
      void refreshWorkspaceFiles();
      setRightTab('changes');
    };
    window.addEventListener('clutch-file-changed', handler);
    return () => window.removeEventListener('clutch-file-changed', handler);
  }, [refreshWorkspaceFiles]);

  // Sidebar selector width for calculations
  const selectedSidebarWidth = sidebarOpen ? SIDEBAR_EXPANDED_WIDTH_PX : SIDEBAR_COLLAPSED_WIDTH_PX;
  const rightSidebarWidth = rightPanelOpen ? 300 : 0;

  const effectiveWorkflowId = selectedWorkflowId || clutchState.workflow_id || '';
  const effectiveWorkflowName = currentFlowName || clutchState.workflow_id || selectedWorkflowId || '';

  useEffect(() => {
    if (!effectiveWorkflowId) {
      setWorkflowAgentSteps([]);
      return;
    }
    let cancelled = false;
    void loadWorkflowById(effectiveWorkflowId)
      .then((workflow) => {
        if (cancelled) return;
        setWorkflowAgentSteps(orderedWorkflowAgentSteps(workflow, configuredAgents));
      })
      .catch(() => {
        if (!cancelled) setWorkflowAgentSteps([]);
      });
    return () => {
      cancelled = true;
    };
  }, [effectiveWorkflowId, configuredAgents]);

  useEffect(() => {
    if (rightTab === 'flow') {
      setRightTab('overview');
    }
  }, [rightTab]);

  const [uncommitted, setUncommitted] = useState<UncommittedFile[]>([]);

  // Close unified settings dialog on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setView(prev => (prev === 'agents' || prev === 'settings' || prev === 'tools' || prev === 'workflows' || prev === 'skills' || prev === 'mcp' || prev === 'models' || prev === 'appearance') ? 'chat' : prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleClearTerminal = () => {
    clutchStore.clearTerminalLogs();
  };

  const handleStopRun = (): boolean => {
    // Workflow (Flow) runs: stop immediately without confirmation.
    // Plain LLM chat runs: ask once to avoid accidental interruption.
    if (!isWorkflowChat && highRiskConfirmEnabled && !highRiskConfirmed) {
      const ok = window.confirm(t('Confirm stopping the current run? This will interrupt the current AI Agent execution.'));
      if (!ok) return false;
      setHighRiskConfirmed(true);
    }
    // Immediate UI: Stop → Continue / idle before WS ack (avoid "stuck" Stop).
    if (!isWorkflowChat) {
      clutchStore.optimisticPlainChatStop();
    }
    void clutchStore.send({ action: 'stop_run' });
    return true;
  };

  const handleContinueRun = () => {
    void clutchStore.send({ action: 'continue_run' });
  };

  const handlePickWorkspace = async () => {
    setWorkspacePickError(null);
    try {
      const path = await pickWorkspaceFolder(t('Select project folder'));
      if (!path) return;
      const info = await addWorkspace(path);
      const listed = await fetchWorkspaces();
      setWorkspaces(listed.workspaces);
      setActiveWorkspaceId(listed.active_id);
      setWorkspace(info);
      await refreshWorkspaceFiles();
      await refreshWorkspaceGit();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Workspace authorize failed';
      setWorkspacePickError(message);
      console.error('[Clutch] workspace authorize failed:', error);
    }
  };

  const handleSelectWorkspace = async (workspaceId: string) => {
    try {
      const info = await activateWorkspace(workspaceId);
      setActiveWorkspaceId(workspaceId);
      setWorkspace(info);
      await refreshWorkspaceFiles();
      await refreshWorkspaceGit();
    } catch (error) {
      console.error('[Clutch] workspace switch failed:', error);
    }
  };

  const handleCreateRepositoryGroup = () => {
    setPromptModal({
      isOpen: true,
      title: t('New project group'),
      placeholder: t('Enter group name...'),
      hasInput: true,
      defaultValue: '',
      onConfirm: async (name) => {
        setPromptModal(null);
        if (!name.trim()) return;
        try {
          const group = await createRepositoryGroup(name.trim());
          setRepositoryGroups((current) => [...current, group]);
        } catch (error) {
          console.error('[Clutch] create repository group failed:', error);
        }
      }
    });
  };

  const handleToggleRepositoryGroup = async (groupId: string, collapsed: boolean) => {
    try {
      const updated = await updateRepositoryGroup(groupId, { collapsed });
      setRepositoryGroups((current) =>
        current.map((group) => (group.id === groupId ? updated : group)),
      );
    } catch (error) {
      console.error('[Clutch] update repository group failed:', error);
    }
  };

  const handleDeleteRepositoryGroup = (groupId: string) => {
    setPromptModal({
      isOpen: true,
      title: t('Delete Group'),
      message: t('Are you sure you want to delete this group?'),
      hasInput: false,
      onConfirm: async () => {
        setPromptModal(null);
        try {
          await deleteRepositoryGroup(groupId);
          const listed = await fetchRepositoryGroups();
          setRepositoryGroups(listed.groups);
        } catch (error) {
          console.error('[Clutch] delete repository group failed:', error);
        }
      }
    });
  };

  const handleRenameRepositoryGroup = (groupId: string) => {
    const currentGroup = repositoryGroups.find(g => g.id === groupId);
    if (!currentGroup) return;

    setPromptModal({
      isOpen: true,
      title: t('Rename Group'),
      placeholder: t('Enter new group name...'),
      defaultValue: currentGroup.name,
      hasInput: true,
      onConfirm: async (newName) => {
        setPromptModal(null);
        if (!newName.trim()) return;
        try {
          const updated = await updateRepositoryGroup(groupId, { name: newName.trim() });
          setRepositoryGroups((current) =>
            current.map((g) => (g.id === groupId ? updated : g))
          );
        } catch (error) {
          console.error('[Clutch] rename repository group failed:', error);
        }
      }
    });
  };

  const handleMoveWorkspaceToGroup = async (workspaceId: string, targetGroupId: string) => {
    const applyMove = (groups: RepositoryGroup[]) =>
      groups.map((group) => {
        const hasId = group.workspace_ids.includes(workspaceId);
        const isTarget = targetGroupId !== '__default__' && group.id === targetGroupId;

        if (isTarget && !hasId) {
          return { ...group, workspace_ids: [...group.workspace_ids, workspaceId] };
        }
        if (!isTarget && hasId) {
          return { ...group, workspace_ids: group.workspace_ids.filter((id) => id !== workspaceId) };
        }
        return group;
      });

    setRepositoryGroups(applyMove);

    try {
      for (const group of repositoryGroups) {
        const hasId = group.workspace_ids.includes(workspaceId);
        const isTarget = targetGroupId !== '__default__' && group.id === targetGroupId;

        if (isTarget && !hasId) {
          const newIds = [...group.workspace_ids, workspaceId];
          await updateRepositoryGroup(group.id, { workspace_ids: newIds });
        } else if (!isTarget && hasId) {
          const newIds = group.workspace_ids.filter((id) => id !== workspaceId);
          await updateRepositoryGroup(group.id, { workspace_ids: newIds });
        }
      }

      const listed = await fetchRepositoryGroups();
      setRepositoryGroups(listed.groups);
    } catch (error) {
      console.error('[Clutch] move workspace to group failed:', error);
      const listed = await fetchRepositoryGroups();
      setRepositoryGroups(listed.groups);
    }
  };

  const handleOpenWorkspaceFile = async (path: string) => {
    try {
      const resolved = await resolveWorkspaceFile(path);
      if (!resolved.ok) {
        setPreviewToast(
          resolved.reason === 'ambiguous'
            ? `Multiple files named “${path}” — open from Files instead.`
            : `File not found: ${path}`,
        );
        window.setTimeout(() => setPreviewToast(null), 3200);
        return;
      }
      // HTML: open rendered page in the system browser (not Clutch source preview).
      if (isHtmlWorkspacePath(resolved.path)) {
        const abs = absoluteWorkspacePath(workspace?.workspace_path, resolved.path);
        if (!abs) {
          setPreviewToast(`Could not resolve path: ${resolved.path}`);
          window.setTimeout(() => setPreviewToast(null), 3200);
          return;
        }
        setPreviewFile(null);
        await openPathInSystem(abs);
        const leaf = resolved.path.split(/[/\\]/).pop() || resolved.path;
        setPreviewToast(`Opened in browser: ${leaf}`);
        window.setTimeout(() => setPreviewToast(null), 2800);
        return;
      }
      if (isImageWorkspacePath(resolved.path)) {
        const mediaSrc = await workspaceMediaUrl(resolved.path);
        setPreviewFile({
          name: resolved.path,
          content: '',
          mediaSrc,
        });
        return;
      }
      const content = await fetchWorkspaceFile(resolved.path);
      setPreviewFile({
        name: resolved.path,
        content,
        plain: isLargePreviewContent(content),
      });
    } catch (error) {
      console.error('[Clutch] read file failed:', error);
      setPreviewToast(`Could not open: ${path}`);
      window.setTimeout(() => setPreviewToast(null), 3200);
    }
  };

  const openWorkspaceFileRef = useRef(handleOpenWorkspaceFile);
  openWorkspaceFileRef.current = handleOpenWorkspaceFile;

  useEffect(() => {
    const handler = (event: Event) => {
      const path = (event as CustomEvent<{ path?: string }>).detail?.path;
      if (!path) return;
      void openWorkspaceFileRef.current(path);
    };
    window.addEventListener('clutch-open-file', handler);
    return () => window.removeEventListener('clutch-open-file', handler);
  }, []);

  const handlePreviewSnippet = (name: string, content: string) => {
    setPreviewFile({
      name,
      content,
      plain: isLargePreviewContent(content),
    });
  };

  const handleApprove = () => {
    void clutchStore.send({ action: 'human_decision', decision: 'approve' });
    setRightTab('overview');
  };

  const handleReject = () => {
    void clutchStore.send({ action: 'human_decision', decision: 'reject' });
  };

  const handleRetryWithInstructions = (instructions: string) => {
    void clutchStore.send({ action: 'human_decision', decision: 'retry', instructions });
    setRightTab('overview');
  };

  const handleAnswerQuestion = (option: { id: string; label: string }) => {
    void clutchStore.send({
      action: 'human_decision',
      decision: 'approve',
      instructions: JSON.stringify({ id: option.id, label: option.label }),
    });
    setRightTab('overview');
  };

  // Permission mode (persisted on backend)
  const [permissionMode, setPermissionMode] = useState<PermissionMode>('auto_edit');

  useEffect(() => {
    void fetchPermissionMode()
      .then((mode) => setPermissionMode(mode))
      .catch(() => {});
  }, []);

  const handlePermissionModeChange = (mode: PermissionMode) => {
    setPermissionMode(mode);
    void savePermissionMode(mode).catch(() => {});
  };

  const [slashNotice, setSlashNotice] = useState<string | null>(null);
  const slashNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dismissSlashNotice = useCallback(() => {
    if (slashNoticeTimerRef.current) clearTimeout(slashNoticeTimerRef.current);
    setSlashNotice(null);
  }, []);

  const showSlashNotice = useCallback((text: string, durationMs = 12000) => {
    setSlashNotice(text);
    if (slashNoticeTimerRef.current) clearTimeout(slashNoticeTimerRef.current);
    // Stay long enough to read; user can also dismiss with X.
    slashNoticeTimerRef.current = setTimeout(() => setSlashNotice(null), durationMs);
  }, []);

  const handleSlashCommand = useCallback(
    async (id: SlashCommandId) => {
      if (id === 'plan') {
        handlePermissionModeChange('plan');
        showSlashNotice('Plan mode on — Agent plans before editing. Switch mode to resume writes.');
        return;
      }
      if (id === 'help') {
        showSlashNotice('/plan · /compact · /todos · /help');
        return;
      }
      if (id === 'todos') {
        const el =
          document.querySelector('[data-testid="todo-sticky-rail"]') ||
          document.querySelector('[data-testid="todo-card"]');
        if (el instanceof HTMLElement) {
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          showSlashNotice('Focused Todo checklist.');
        } else {
          showSlashNotice('No Todo checklist in this chat yet.');
        }
        return;
      }
      if (id === 'compact') {
        if (!sessionRunId) {
          showSlashNotice('No active session to compact.');
          return;
        }
        try {
          const result = await compactRun(sessionRunId);
          showSlashNotice(
            result.compacted
              ? `压缩完成 · 见对话末尾 /compact + 摘要（${result.message_count} 条）`
              : result.detail || 'Nothing to compact yet.',
          );
          if (result.compacted) {
            // Let WS patch apply, then scroll to the digest at the end of the feed.
            window.setTimeout(() => {
              const el = document.querySelector('[data-testid="compaction-digest"]');
              if (el instanceof HTMLElement) {
                el.scrollIntoView({ behavior: 'smooth', block: 'end' });
              }
            }, 120);
          }
        } catch (err) {
          showSlashNotice(err instanceof Error ? err.message : 'Compact failed.');
        }
      }
    },
    [sessionRunId, showSlashNotice],
  );

  // Skills list for / command picker in chat input
  const [chatSkills, setChatSkills] = useState<ScannedSkill[]>([]);

  useEffect(() => {
    void fetchSkillsRegistry()
      .then((data) => setChatSkills(data.skills))
      .catch(() => {});
  }, []);

  const bindWorkflowForChat = useCallback((workflowId: string, workflowName: string) => {
    setIsMultiAgent(true);
    setSelectedWorkflowId(workflowId);
    setCurrentFlowName(workflowName);
    setSelectedAgentId(null);
    localStorage.removeItem('clutch_active_agent_id');
    setInputValue(formatInputMention(workflowName));
  }, []);

  const handleFlowSelect = (flow: string) => {
    bindWorkflowForChat(flow, flow);
  };

  const handleUseWorkflowInChat = (workflowId: string, workflowName: string) => {
    bindWorkflowForChat(workflowId, workflowName);
    setView('chat');
  };

  const toggleWorkflowMenu = async () => {
    const next = !workflowMenuOpen;
    closeFooterMenus();
    setWorkflowMenuOpen(next);
    if (next) {
      try {
        const items = await listWorkflowItems();
        setFooterWorkflows(items.map((item) => ({ id: item.id, name: item.name })));
      } catch {
        setFooterWorkflows([]);
      }
    }
  };

  const toggleModelMenu = () => {
    const next = !modelMenuOpen;
    closeFooterMenus();
    setModelMenuOpen(next);
    if (next) {
      void syncModelsConfig().catch(() => {});
    }
  };

  const toggleAgentMenu = () => {
    const next = !agentMenuOpen;
    closeFooterMenus();
    setAgentMenuOpen(next);
  };

  const handleFooterModelSelect = (modelId: string) => {
    const model = configuredModels.find((item) => item.id === modelId);
    if (!model) return;
    setModelMenuOpen(false);
    setActiveModelId(modelId);
    setSelectedModel(model.name);
    if (isTurnInProgress) {
      setPendingFooterModelId(modelId);
      return;
    }
    void (async () => {
      try {
        await saveModelsConfig({ active_model_id: modelId });
        await syncModelsConfig();
      } catch (error) {
        console.error('[Clutch] model switch failed:', error);
        setWorkspacePickError(
          error instanceof Error ? error.message : t('Failed to switch model.'),
        );
        await syncModelsConfig().catch(() => {});
      }
    })();
  };

  const handleFooterAgentSelect = (agent: Agent) => {
    handleActivateAgent(agent);
    setAgentMenuOpen(false);
  };

  const discardEmptySessionIfNeeded = async (runId: string) => {
    const snapshot = clutchStore.getSnapshot();
    if (snapshot.run_id !== runId || sessionHasPersistableContent(snapshot)) return;

    // Design content lives under .clutch/design — not clutchStore messages.
    const local = sessions.find((s) => s.run_id === runId);
    const treatAsDesign = local?.mode === 'design' || appMode === 'design';
    if (treatAsDesign) {
      try {
        const design = await getDesignSession(runId);
        const hasDesignWork = Boolean(
          design.spec ||
            (design.screens && design.screens.length > 0) ||
            design.reference_image_url ||
            design.reference_md_text ||
            design.reference_url ||
            (design.prompt && design.prompt.trim()) ||
            design.status === 'ready' ||
            design.status === 'crafting_spec' ||
            design.status === 'generating_ui' ||
            design.status === 'iterating' ||
            (design.artifact_paths && design.artifact_paths.length > 0),
        );
        if (hasDesignWork) return;
      } catch {
        // No design session on disk — empty draft may be discarded.
      }
    }

    try {
      await deleteSession(runId);
      setSessions((prev) => prev.filter((session) => session.run_id !== runId));
    } catch {
      // Session was never persisted — safe to ignore.
    }
  };

  /** Default-title Design drafts with no real UI preview — cleaned up when spawning New Design. */
  const isEmptyDesignDraft = useCallback(
    (s: SessionRecord) => {
      if (s.mode !== 'design') return false;
      if (s.ui_preview_url || s.thumbnail_url) return false;
      const title = (s.title || '').trim();
      const status = (s.status || '').trim().toLowerCase();
      const defaultTitle =
        !title || title === t('New Design') || title === 'New Design' || title === '新建设计';
      if (!defaultTitle) return false;
      // "ready" without thumbnail is the false-ready from welcome mount.
      return status === '' || status === 'idle' || status === 'draft' || status === 'ready';
    },
    [t],
  );

  const openDesignSession = useCallback(
    (runId: string, title: string) => {
      setSessionRunId(runId);
      setHistorySessionViewRunId(null);
      setHighlightedDispatchEntryId(null);
      setHighlightedLogIndex(null);
      setCurrentFlowName(title);
      setSelectedWorkflowId(null);
      setAppMode('design');
      setView('chat');
      setWorkspaceViewMode('chat');
      saveWorkspaceViewMode('chat');
      setRightTab('overview');
      setRightPanelOpen(false);
      void clutchStore.connect(runId);
    },
    [],
  );

  const handleNewChat = async () => {
    if (!workspace) {
      await handlePickWorkspace();
      return;
    }
    const startNewChat = async () => {
      // Switch to chat immediately. Waiting until after discardEmptySessionIfNeeded
      // races desktop E2E (and users) who open Settings before the API call returns —
      // the late setView('chat') would close the preferences modal.
      setView('chat');
      await discardEmptySessionIfNeeded(sessionRunId);
      scheduleBackgroundHydrateForRun(sessionRunId);
      const runId = createSessionRunId();
      setSessionRunId(runId);
      setHistorySessionViewRunId(null);
      setHighlightedDispatchEntryId(null);
      setHighlightedLogIndex(null);
      setCurrentFlowName('');
      setSelectedWorkflowId(null);
      if (workspaceViewMode !== 'terminal') {
        selectDefaultAgent();
      }
      setAppMode('coding');
      setRightTab('overview');
      void createSession({
        run_id: runId,
        title: t('New session'),
        mode: 'coding',
      }).catch(() => {});
      void (async () => {
        try {
          const config = await fetchModelsConfig();
          const defaultTextModelId = resolveDefaultTextModelId(config);
          if (defaultTextModelId && defaultTextModelId !== config.active_model_id) {
            await saveModelsConfig({ active_model_id: defaultTextModelId });
          }
          await syncModelsConfig();
        } catch (error) {
          console.warn('[Clutch] reset default text model on new chat failed:', error);
        }
      })();
      void clutchStore.connect(runId);
      void refreshSessions('coding');
    };

    if (shouldConfirmLeavingTerminalForNewChat(clutchState, workspaceViewMode, inputValue, mentionableAgents)) {
      promptLeaveTerminal(() => {
        setWorkspaceViewMode('chat');
        saveWorkspaceViewMode('chat');
        void startNewChat();
      });
      return;
    }
    await startNewChat();
  };

  const handleNewDesign = async () => {
    if (!workspace) {
      await handlePickWorkspace();
      return;
    }

    const emptyTitle = t('New Design');
    // Always spawn a fresh welcome row at the top. Reusing an old empty draft kept its
    // started_at / history position, so "New Design" could sit under newer real sessions.
    const empties = sessions.filter(isEmptyDesignDraft);
    if (sessionRunId && !empties.some((s) => s.run_id === sessionRunId)) {
      await discardEmptySessionIfNeeded(sessionRunId);
      scheduleBackgroundHydrateForRun(sessionRunId);
    }
    if (empties.length > 0) {
      await Promise.all(
        empties.map(async (s) => {
          try {
            await deleteSession(s.run_id);
          } catch {
            /* already gone */
          }
        }),
      );
      const drop = new Set(empties.map((s) => s.run_id));
      setSessions((prev) => prev.filter((s) => !drop.has(s.run_id)));
    }

    const runId = createSessionRunId();
    openDesignSession(runId, emptyTitle);
    upsertLocalSession(runId, emptyTitle, { mode: 'design', status: 'idle' });
    void createSession({
      run_id: runId,
      title: emptyTitle,
      mode: 'design',
      status: 'idle',
    }).catch((error) => {
      console.warn('[Clutch] design session register failed:', error);
    });
    void refreshSessions('design');
  };

  const handleDesignBusyChange = useCallback(
    (generating: boolean, meta?: { device?: 'web' | 'app' }) => {
      if (generating) {
        const device =
          meta?.device === 'app' || meta?.device === 'web' ? meta.device : undefined;
        setSessions((prev) =>
          prev.map((s) =>
            s.run_id === sessionRunId
              ? {
                  ...s,
                  status: 'running',
                  mode: 'design' as const,
                  ...(device ? { device } : {}),
                }
              : s,
          ),
        );
        void createSession({
          run_id: sessionRunId,
          title: currentFlowName || t('New Design'),
          mode: 'design',
          status: 'running',
        }).catch(() => {});
        return;
      }

      void (async () => {
        let hasDesignWork = false;
        let designDevice: string | null = null;
        let designThumb: string | null = null;
        let designPreview: string | null = null;
        try {
          const design = await getDesignSession(sessionRunId);
          hasDesignWork = Boolean(
            design.spec ||
              (design.screens && design.screens.length > 0) ||
              design.reference_image_url ||
              design.reference_md_text ||
              design.reference_url ||
              (design.prompt && design.prompt.trim()) ||
              design.status === 'ready' ||
              design.status === 'crafting_spec' ||
              design.status === 'generating_ui' ||
              design.status === 'iterating' ||
              (design.artifact_paths && design.artifact_paths.length > 0),
          );
          if (design.device === 'app' || design.device === 'web') {
            designDevice = design.device;
          }
          if (design.thumbnail_url) {
            designThumb = design.thumbnail_url;
          }
          if (design.ui_preview_url) {
            designPreview = design.ui_preview_url;
          }
        } catch {
          hasDesignWork = false;
        }

        // Welcome draft finished "not busy" — stay idle so history can prune extras.
        if (!hasDesignWork) {
          setSessions((prev) =>
            prev.map((s) =>
              s.run_id === sessionRunId ? { ...s, status: 'idle', mode: 'design' as const } : s,
            ),
          );
          void createSession({
            run_id: sessionRunId,
            title: currentFlowName || t('New Design'),
            mode: 'design',
            status: 'idle',
          }).catch(() => {});
          return;
        }

        setSessions((prev) =>
          prev.map((s) =>
            s.run_id === sessionRunId
              ? {
                  ...s,
                  status: 'ready',
                  mode: 'design' as const,
                  ...(designDevice ? { device: designDevice } : {}),
                  ...(designThumb ? { thumbnail_url: designThumb } : {}),
                  ...(designPreview ? { ui_preview_url: designPreview } : {}),
                }
              : s,
          ),
        );
        try {
          await createSession({
            run_id: sessionRunId,
            title: currentFlowName || t('New Design'),
            mode: 'design',
            status: 'ready',
          });
        } catch {
          /* keep local status */
        }
        const updated = await fetchSessions(
          resolveSessionHistoryWorkspaceId({ allWorkspaces: true }),
          'design',
        ).catch(() => null);
        if (updated) {
          setSessions(
            updated.map((s) =>
              s.run_id === sessionRunId ? { ...s, status: 'ready', mode: 'design' as const } : s,
            ),
          );
        }
        void refreshWorkspaceFiles();
        try {
          const session = await getDesignSession(sessionRunId);
          const paths = session.artifact_paths?.filter(Boolean) ?? [];
          if (paths.length === 0) return;
          setUncommitted((prev) => {
            const next = [...prev];
            for (const path of paths) {
              const idx = next.findIndex((f) => f.name === path);
              const entry: UncommittedFile = {
                name: path,
                status: 'A',
                diffs: [{ type: 'addition', text: path, lineNum: 1 }],
                active: true,
              };
              if (idx >= 0) next[idx] = entry;
              else next.push(entry);
            }
            return next;
          });
          setRightTab('changes');
        } catch {
          /* ignore — Files refresh still ran */
        }
      })();
    },
    [sessionRunId, currentFlowName, t, refreshWorkspaceFiles],
  );

  const handleAppModeChange = (mode: AppWorkspaceMode) => {
    if (mode === appMode) return;
    if (mode === 'design') {
      // Design defaults to a collapsed right rail (Files / Changes still available).
      setRightPanelOpen(false);
      void handleNewDesign();
      return;
    }
    setAppMode('coding');
    setView('chat');
    void (async () => {
      // Leaving Design: drop the empty welcome draft so it doesn't pile up.
      await discardEmptySessionIfNeeded(sessionRunId);
      try {
        const codingSessions = await fetchSessions(
          resolveSessionHistoryWorkspaceId({ allWorkspaces: true }),
          'coding',
        );
        setSessions(codingSessions);
        const currentIsDesign = sessions.find((s) => s.run_id === sessionRunId)?.mode === 'design';
        if (currentIsDesign && codingSessions.length > 0) {
          const inActive = codingSessions.filter((s) => s.workspace_id === activeWorkspaceId);
          await applySelectedSession(inActive[0] ?? codingSessions[0]);
          return;
        }
      } catch {
        void refreshSessions('coding');
      }
    })();
  };

  const applySelectedSession = async (session: SessionRecord) => {
    setLoadingSessionId(session.run_id);
    const sessionMode: AppWorkspaceMode = session.mode === 'design' ? 'design' : 'coding';
    setAppMode(sessionMode);
    setView('chat');
    setHighlightedDispatchEntryId(null);
    setHighlightedLogIndex(null);
    try {
      if (session.workspace_id && session.workspace_id !== activeWorkspaceId) {
        await handleSelectWorkspace(session.workspace_id);
      }
      if (session.run_id !== sessionRunId) {
        void discardEmptySessionIfNeeded(sessionRunId);
        scheduleBackgroundHydrateForRun(sessionRunId);
      }

      const storedFlowId = localStorage.getItem(`clutch_session_flow_${session.run_id}`);
      const storedAgentId = localStorage.getItem(`clutch_session_agent_${session.run_id}`);

      setIsMultiAgent(true);

      let hydratedState: ClutchState | null = null;
      if (sessionMode === 'coding') {
        try {
          const { state } = await fetchRunState(session.run_id);
          hydratedState = normalizeTerminalSessionForResume(state);
          clutchStore.setPendingHydrate(hydratedState);
        } catch (error) {
          console.warn('[Clutch] session state hydrate failed:', error);
        }
      }

      setSessionRunId(session.run_id);
      setHistorySessionViewRunId(session.run_id);
      if (sessionMode === 'design') {
        setCurrentFlowName(session.title || t('New Design'));
        setSelectedWorkflowId(null);
        setWorkspaceViewMode('chat');
        saveWorkspaceViewMode('chat');
        void clutchStore.connect(session.run_id);
        return;
      }

      setWorkspaceViewMode('chat');
      saveWorkspaceViewMode('chat');

      if (storedFlowId !== null) {
        setSelectedWorkflowId(storedFlowId || null);
        const matched = footerWorkflows.find((w) => w.id === storedFlowId);
        setCurrentFlowName(matched ? matched.name : (storedFlowId || ''));
      } else {
        const matched = footerWorkflows.find((w) => w.id === session.workflow_id);
        setCurrentFlowName(matched ? matched.name : (session.workflow_id || ''));
        setSelectedWorkflowId(session.workflow_id || null);
      }

      if (storedAgentId !== null) {
        setSelectedAgentId(storedAgentId || null);
      } else {
        const stateAgentId = hydratedState?.cli_session_agent_id || hydratedState?.claude_session_agent_id;
        if (stateAgentId) {
          setSelectedAgentId(stateAgentId);
        } else if (session.workflow_id) {
          setSelectedAgentId(null);
        } else {
          const storedGlobalAgentId = localStorage.getItem('clutch_active_agent_id');
          setSelectedAgentId(storedGlobalAgentId || BUILTIN_AGENT_ID);
        }
      }

      if (sessionHasTerminalHistory(hydratedState ?? {})) {
        setWorkspaceViewMode('chat');
        saveWorkspaceViewMode('chat');
      }
    } finally {
      setLoadingSessionId(null);
    }
  };

  const handleSelectSession = async (session: SessionRecord) => {
    if (session.run_id === sessionRunId) return;

    const proceed = async () => {
      await applySelectedSession(session);
    };

    if (shouldConfirmLeavingTerminal(clutchState, workspaceViewMode, inputValue, mentionableAgents)) {
      promptLeaveTerminal(() => {
        setWorkspaceViewMode('chat');
        saveWorkspaceViewMode('chat');
        void proceed();
      });
      return;
    }
    await proceed();
  };

  const handleNewChatInWorkspace = async (workspaceId: string) => {
    if (workspaceId !== activeWorkspaceId) {
      await handleSelectWorkspace(workspaceId);
    }
    if (appMode === 'design') {
      await handleNewDesign();
      return;
    }
    await handleNewChat();
  };

  const handleDeleteWorkspace = (workspaceId: string) => {
    setPromptModal({
      isOpen: true,
      title: t('Delete project'),
      message: t('Are you sure you want to remove this project from the list?'),
      hasInput: false,
      onConfirm: async () => {
        setPromptModal(null);
        try {
          await removeWorkspace(workspaceId);
          const listed = await fetchWorkspaces();
          setWorkspaces(listed.workspaces);
          setActiveWorkspaceId(listed.active_id);
          const active = listed.workspaces.find((item) => item.id === listed.active_id) ?? null;
          setWorkspace(active);
          if (active) {
            await refreshWorkspaceFiles();
            await refreshWorkspaceGit();
          } else {
            setWorkspaceFiles([]);
            setWorkspaceGit({ branch: null, branches: [] });
          }
          const groupsListed = await fetchRepositoryGroups();
          setRepositoryGroups(groupsListed.groups);

          await refreshSessions();
        } catch (error) {
          console.error('[Clutch] remove workspace failed:', error);
        }
      }
    });
  };

  const handleDeleteSession = (runId: string) => {
    setPromptModal({
      isOpen: true,
      title: t('Delete session'),
      message: t('Are you sure you want to permanently delete this session?'),
      hasInput: false,
      onConfirm: async () => {
        setPromptModal(null);
        try {
          await deleteSession(runId);
          const updatedSessions = await fetchSessions(
            resolveSessionHistoryWorkspaceId({ allWorkspaces: true }),
            appMode,
          );
          setSessions(updatedSessions);

          if (sessionRunId === runId) {
            const remainingWorkspaceSessions = updatedSessions.filter(
              (s) => s.workspace_id === activeWorkspaceId && s.run_id !== runId
            );

            if (remainingWorkspaceSessions.length > 0) {
              await handleSelectSession(remainingWorkspaceSessions[0]);
            } else if (appMode === 'design') {
              await handleNewDesign();
            } else {
              const tempRunId = createSessionRunId();
              setSessionRunId(tempRunId);
              setHistorySessionViewRunId(null);
              setCurrentFlowName('');
              setSelectedWorkflowId(null);
              setView('chat');
              setRightTab('overview');
              void clutchStore.connect(tempRunId);
            }
          }
        } catch (error) {
          console.error('[Clutch] delete session failed:', error);
        }
      }
    });
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;
    if (!workspace) {
      setWorkspacePickError(t('Select a project before starting a conversation.'));
      return;
    }
    if (
      clutchState.workflow_id
      && shouldRouteWorkflowRefine(clutchState.status, clutchState.workflow_id, text)
    ) {
      setWorkspacePickError(null);
      registerSessionAfterSend(sessionRunId, text);
      const mentionAgentId = resolveWorkflowMentionAgentId(
        text,
        workflowAgentSteps,
        configuredAgents,
      );
      void submitChatMessage(text, mentionAgentId ?? clutchState.refine_agent_id ?? undefined).catch((error) => {
        console.error('[Clutch] refine message failed:', error);
      });
      return;
    }
    if (!isMultiAgent) {
      if (!selectedAgentId) {
        setWorkspacePickError(t('Select an AI Agent before sending.'));
        setView('agents');
        return;
      }
    } else {
      const hasWorkflow = Boolean(
        (selectedWorkflowId && !clutchState.workflow_id) || clutchState.workflow_id,
      );
      if (!hasWorkflow && !selectedAgentId) {
        setWorkspacePickError(t('Select an AI Agent or a Workflow before sending.'));
        return;
      }
    }
    if (selectedWorkflowId && !clutchState.workflow_id) {
      const workflowId = selectedWorkflowId;
      const instruction = text.trim();
      setWorkspacePickError(null);
      registerSessionAfterSend(sessionRunId, instruction, {
        workflowId: workflowId,
      });
      clutchStore.optimisticWorkflowStart({
        runId: sessionRunId,
        workflowId,
        instruction,
        activeAgent: workflowAgentSteps[0]?.agentName || undefined,
      });
      void (async () => {
        try {
          if (!clutchStore.connected) {
            await clutchStore.connect(sessionRunId);
          }
          setSessions(prev =>
            prev.map(s => s.run_id === sessionRunId ? { ...s, status: 'running' } : s)
          );
          const result = await startWorkflowRun(sessionRunId, workflowId, instruction);
          clutchStore.mergeWorkflowComplete(result.state);
          setSelectedWorkflowId(null);
          void refreshSessions();
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Failed to start workflow';
          setWorkspacePickError(message);
          clutchStore.replaceState({
            ...clutchStore.getSnapshot(),
            status: 'failed',
          });
          console.error('[Clutch] workflow start failed:', error);
        }
      })();
      return;
    }
    const sendingAgent = configuredAgents.find((agent) => agent.id === selectedAgentId);
    const sendingBoundModelId =
      sendingAgent && !isBuiltinAgent(sendingAgent) && sendingAgent.modelId
        ? sendingAgent.modelId
        : undefined;
    const sendingModelId = sendingBoundModelId ?? footerEffectiveModelId ?? null;
    const sendingModel = configuredModels.find((model) => model.id === sendingModelId);
    const sendingCustomEngineLabel =
      sendingAgent && !isClutchAgentType(sendingAgent)
        ? agentTypeLabel(agentTypeFromAgent(sendingAgent))
        : '';
    inFlightTurnRef.current = {
      agentId: selectedAgentId,
      agentName: getAgentDisplayName(sendingAgent),
      modelId: sendingModelId,
      modelName: sendingModel?.name ?? selectedModel ?? '',
      engineHint: sendingCustomEngineLabel
        ? configuredEngineToRuntimeLabel(sendingCustomEngineLabel)
        : (sendingModel?.name ?? selectedModel ?? ''),
    };
    const clientMessageId = clutchStore.optimisticPlainChatSend(text.trim());
    registerSessionAfterSend(sessionRunId, text);
    void submitChatMessage(
      text,
      selectedAgentId,
      sendingBoundModelId ? undefined : sendingModelId || undefined,
      clientMessageId,
    ).catch((error) => {
      console.error('[Clutch] chat message failed:', error);
      setWorkspacePickError(
        error instanceof Error ? error.message : t('Failed to send message.'),
      );
    });
  };

  const handleClearSessionView = () => {
    setRightTab('overview');
    setCurrentFlowName('');
  };

  useEffect(() => {
    if (clutchState.workflow_id) {
      const matched = footerWorkflows.find((w) => w.id === clutchState.workflow_id);
      setCurrentFlowName(matched ? matched.name : clutchState.workflow_id);
    }
  }, [clutchState.workflow_id, footerWorkflows]);

  const currentThemeObj = THEME_PRESETS.find(t => t.id === themeId) || THEME_PRESETS[0];
  const themeVars = currentThemeObj.variables;

  const activeSession = sessions.find(s => s.run_id === sessionRunId);
  const sessionTitle = activeSession ? (activeSession.title || activeSession.workflow_id || activeSession.run_id) : '';

  return (
    <div 
      style={themeVars as React.CSSProperties}
      data-platform={hostOs}
      data-font-size={fontSize}
      className="relative h-screen max-h-screen bg-background text-on-surface overflow-hidden flex flex-col font-sans select-none"
    >
      {/* 1. Header component */}
      <Header
        currentFlow={currentFlowName || clutchState.workflow_id || (appMode === 'design' ? t('New Design') : t('New session'))}
        workspaceName={workspace?.name}
        onPickWorkspace={() => { void handlePickWorkspace(); }}
        folders={folders}
        sidebarOpen={sidebarOpen}
        appMode={appMode}
        onAppModeChange={handleAppModeChange}
      />

      {!isWindows ? (
      <ChromeEdgeToggle
        testId="workspace-sidebar-toggle"
        icon={sidebarOpen ? 'chevron_left' : 'chevron_right'}
        title={sidebarOpen ? t('Collapse Sidebar') : t('Expand Sidebar')}
        onClick={() => setSidebarOpen((open) => !open)}
        className="fixed transition-[left] duration-300 ease-out"
        style={{
          top: CHROME_PANEL_TOGGLE_TOP_CSS,
          left: selectedSidebarWidth - CHROME_PANEL_TOGGLE_HALF_PX,
        }}
      />
      ) : null}

      {/* 2. Side Panel components layout */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left navigation drawer */}
        <Sidebar
          currentView={currentView}
          setView={setView}
          folders={folders}
          setFolders={setFolders}
          activeFlow={currentFlowName}
          setActiveFlow={handleFlowSelect}
          appMode={appMode}
          onNewChat={() => {
            if (appMode === 'design') {
              void handleNewDesign();
            } else {
              void handleNewChat();
            }
          }}
          isOpenState={sidebarOpen}
          setIsOpenState={setSidebarOpen}
          isMultiAgent={isMultiAgent}
          sessions={sessions}
          shellSnapshotRunIds={shellSnapshotRunIds}
          activeSessionId={sessionRunId}
          loadingSessionId={loadingSessionId}
          clutchStatus={clutchStatus}
          workspaces={workspaces}
          repositoryGroups={repositoryGroups}
          activeWorkspaceId={activeWorkspaceId}
          onAddWorkspace={() => { void handlePickWorkspace(); }}
          onCreateRepositoryGroup={() => { void handleCreateRepositoryGroup(); }}
          onToggleRepositoryGroup={(groupId, collapsed) => {
            void handleToggleRepositoryGroup(groupId, collapsed);
          }}
          onSelectWorkspace={(id) => { void handleSelectWorkspace(id); }}
          onSelectSession={(session) => { void handleSelectSession(session); }}
          onNewChatInWorkspace={(id) => { void handleNewChatInWorkspace(id); }}
          onDeleteWorkspace={(id) => { void handleDeleteWorkspace(id); }}
          onDeleteSession={(id) => { void handleDeleteSession(id); }}
          onDeleteRepositoryGroup={(groupId) => { handleDeleteRepositoryGroup(groupId); }}
          onRenameRepositoryGroup={(groupId) => { handleRenameRepositoryGroup(groupId); }}
          onMoveWorkspaceToGroup={(wsId, grpId) => { void handleMoveWorkspaceToGroup(wsId, grpId); }}
        />

        {/* Main workspace + right rail (Coding chat / Design canvas / file preview) */}
        {previewFile ? (
            <div 
              style={{ paddingLeft: `${selectedSidebarWidth}px`, paddingRight: `${rightSidebarWidth}px`, paddingTop: CONTENT_TOP_WITH_BANNER }}
              className="flex-1 flex flex-col bg-white h-screen overflow-hidden animate-fade-in relative z-30 transition-all duration-300"
            >
              {/* File Preview Header */}
              <div className="h-14 border-b border-outline-variant/60 flex items-center justify-between px-6 bg-neutral-50/50 flex-shrink-0 select-none">
                <div className="flex items-center gap-3">
                  <LegacyIcon
                    name={
                      previewFile.mediaSrc
                        ? 'image'
                        : previewFile.name.endsWith('.md')
                          ? 'markdown'
                          : 'code'
                    }
                    className="text-[20px] text-neutral-500"
                  />
                  <div className="flex flex-col justify-center">
                    <h3 className="text-xs font-bold text-neutral-900 font-mono tracking-tight flex items-center gap-1">
                      {previewFile.name.includes('/') && (
                        <span className="text-neutral-400 font-medium">{previewFile.name.split('/').slice(0, -1).join('/')}/</span>
                      )}
                      <span>{previewFile.name.split('/').pop()}</span>
                    </h3>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      if (previewFile.mediaSrc) {
                        void navigator.clipboard.writeText(previewFile.name);
                        return;
                      }
                      void navigator.clipboard.writeText(previewFile.content);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-neutral-500 hover:text-neutral-900 hover:bg-neutral-200/50 rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    <LegacyIcon name="content_copy" className="text-[16px]" />
                    Copy
                  </button>
                  <button
                    type="button"
                    onClick={() => setPreviewFile(null)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-neutral-500 hover:text-neutral-900 hover:bg-neutral-200/50 rounded-lg text-[11px] font-semibold transition-colors"
                  >
                    <LegacyIcon name="close" className="text-[16px]" />
                    Close
                  </button>
                </div>
              </div>

              {/* Code/Markdown/Image Content Viewer */}
              <div className="flex-1 overflow-y-auto p-8 font-mono text-xs text-neutral-800 bg-[#f9f9f9] select-text leading-relaxed">
                {previewFile.mediaSrc ? (
                  <div className="max-w-5xl mx-auto flex items-center justify-center min-h-[calc(100vh-10rem)]">
                    <img
                      src={previewFile.mediaSrc}
                      alt={previewFile.name}
                      className="max-h-[calc(100vh-12rem)] max-w-full object-contain rounded-xl border border-outline-variant/40 bg-white shadow-sm"
                    />
                  </div>
                ) : previewFile.plain ? (
                  <div className="max-w-4xl mx-auto space-y-2">
                    <p className="text-[11px] font-semibold text-neutral-500 font-sans">
                      Large file: plain view
                    </p>
                    <pre className="bg-neutral-900 text-neutral-200 p-6 rounded-xl text-[11px] shadow-sm overflow-auto max-h-[calc(100vh-10rem)] whitespace-pre border border-neutral-800">
                      {previewFile.content}
                    </pre>
                  </div>
                ) : previewFile.name.endsWith('.md') ? (
                  <div className="max-w-3xl mx-auto space-y-3 font-sans text-[13px] text-neutral-700 leading-relaxed bg-white border border-outline p-8 rounded-xl shadow-xs">
                    {previewFile.content.split('\n').map((line, i) => {
                      if (line.startsWith('# ')) {
                        return <h1 key={i} className="text-lg font-bold text-neutral-900 border-b border-outline pb-3 mb-4 flex items-center gap-2">{line.replace('# ', '')}</h1>;
                      }
                      if (line.startsWith('## ')) {
                        return <h2 key={i} className="text-sm font-bold text-neutral-900 mt-5 mb-2 flex items-center gap-2">{line.replace('## ', '')}</h2>;
                      }
                      if (line.startsWith('### ')) {
                        return <h3 key={i} className="text-xs font-bold text-neutral-800 mt-4 mb-1.5">{line.replace('### ', '')}</h3>;
                      }
                      if (line.startsWith('- ')) {
                        let htmlContent = line.replace('- ', '');
                        htmlContent = htmlContent.replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-900 font-semibold">$1</strong>');
                        htmlContent = htmlContent.replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1 py-0.5 rounded font-mono text-[11px] border border-neutral-200/60 mx-0.5">$1</code>');
                        htmlContent = htmlContent.replace(/\[\[(.*?)\]\]/g, '<span class="text-[#897FDB] font-medium hover:underline cursor-pointer">[[ $1 ]]</span>');
                        
                        return (
                          <div key={i} className="flex items-start gap-2 pl-1 my-1.5 text-neutral-600">
                            <span className="w-1 h-1.5 mt-2 rounded bg-neutral-400 flex-shrink-0" />
                            <span dangerouslySetInnerHTML={{ __html: htmlContent }} />
                          </div>
                        );
                      }
                      
                      const pContent = line.replace(/\*\*(.*?)\*\*/g, '<strong class="text-neutral-900 font-semibold">$1</strong>').replace(/`([^`]+)`/g, '<code class="bg-neutral-100 text-neutral-900 px-1 py-0.5 rounded font-mono text-[11px] border border-neutral-200/60 mx-0.5">$1</code>');
                      return <p key={i} className={line.trim() ? "my-2 text-neutral-600" : "h-1"} dangerouslySetInnerHTML={{ __html: pContent }} />;
                    })}
                  </div>
                ) : (
                  <div className="max-w-4xl mx-auto bg-neutral-900 text-neutral-200 p-6 rounded-xl font-mono text-[11px] shadow-sm select-text overflow-x-auto border border-neutral-800">
                    <table className="w-full">
                      <tbody>
                        {previewFile.content.split('\n').map((line, index) => (
                          <tr key={index} className="hover:bg-neutral-800/40 leading-relaxed">
                            <td className="text-neutral-500 text-right pr-4 select-none w-8 border-r border-neutral-800 text-[10px] font-semibold">{index + 1}</td>
                            <td className="pl-4 whitespace-pre font-mono text-neutral-300">{line || ' '}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
        ) : appMode === 'design' ? (
          <div
            style={{
              paddingLeft: `${selectedSidebarWidth}px`,
              paddingRight: `${rightSidebarWidth}px`,
              paddingTop: CONTENT_TOP_WITH_BANNER,
              paddingBottom: '32px',
            }}
            className="flex-1 flex flex-col h-screen overflow-hidden relative z-20 transition-all duration-300"
          >
            <DesignWorkspace
              key={sessionRunId}
              runId={sessionRunId}
              workspaceReady={Boolean(workspace)}
              modelLabel={selectedModel}
              onOpenModels={() => setView('models')}
              onBusyChange={handleDesignBusyChange}
              onSessionTitle={(title, meta) => {
                setCurrentFlowName(title);
                // Title + device — never force status=running (races with ready after generate).
                const device =
                  meta?.device === 'app' || meta?.device === 'web' ? meta.device : undefined;
                setSessions((prev) =>
                  prev.map((s) =>
                    s.run_id === sessionRunId
                      ? {
                          ...s,
                          title: title.slice(0, 80),
                          mode: 'design' as const,
                          ...(device ? { device } : {}),
                        }
                      : s,
                  ),
                );
                void createSession({
                  run_id: sessionRunId,
                  title,
                  mode: 'design',
                }).catch(() => {});
              }}
              onSendToCoding={(handoff: CodingHandoff) => {
                void (async () => {
                  await handleNewChat();
                  setInputValue(handoff.instruction);
                  setAppMode('coding');
                  setView('chat');
                })();
              }}
            />
          </div>
        ) : (
            <>
              <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
              <ChatFeed
                messages={chatMessages}
                hybridExecutions={clutchState.hybrid_executions}
                inputValue={inputValue}
                setInputValue={setInputValue}
                onSendMessage={handleSendMessage}
                sessionTitle={sessionTitle}
                sessionRunId={sessionRunId}
                clutchStatus={clutchStatus}
                currentFlowName={currentFlowName || clutchState.workflow_id}
                selectedSidebarWidth={selectedSidebarWidth}
                rightSidebarWidth={rightSidebarWidth}
                sidebarOpen={sidebarOpen}
                rightPanelOpen={rightPanelOpen}
                onStopRun={handleStopRun}
                onContinueRun={handleContinueRun}
                isMultiAgent={isMultiAgent}
                onApprove={handleApprove}
                onReject={handleReject}
                onRetryWithInstructions={handleRetryWithInstructions}
                onAnswerQuestion={handleAnswerQuestion}
                workspaceAuthorized={Boolean(workspace)}
                onPickWorkspace={() => { void handlePickWorkspace(); }}
                onOpenWorkflows={() => setView('workflows')}
                workspacePickError={workspacePickError}
                selectedWorkflowId={selectedWorkflowId}
                selectedWorkflowName={currentFlowName}
                onClearSelectedWorkflow={() => {
                  clearWorkflowSelection();
                  selectDefaultAgent();
                }}
                activeWorkflowId={clutchState.workflow_id}
                llmModelName={chatLlmModelName}
                activeAgentName={chatActiveAgentName}
                activeAgentAvatar={chatActiveAgentAvatar}
                activeNodeId={clutchState.active_node_id}
                workflowAgentSteps={workflowAgentSteps}
                resolveAgentLogo={resolveAgentLogo}
                engineHint={chatRuntimeEngineHint}
                activeAgentType={selectedAgent ? agentTypeFromAgent(selectedAgent) : ''}
                workspaceViewMode={workspaceViewMode}
                onWorkspaceViewModeChange={handleWorkspaceViewModeChange}
                onLeaveTerminalConfirm={promptLeaveTerminal}
                highlightedDispatchEntryId={highlightedDispatchEntryId}
                hasCliAgents={hasCliAgents}
                workspaceFiles={workspaceFiles}
                sessions={sessions}
                skills={chatSkills}
                permissionMode={permissionMode}
                onPermissionModeChange={handlePermissionModeChange}
                shellSessionStatus={clutchState.shell_session_status}
                shellPoolBlockerRunIds={clutchState.shell_pool_blocker_run_ids}
                shellPoolBlockers={clutchState.shell_pool_blockers}
                shellPoolQueuePosition={clutchState.shell_pool_queue_position}
                shellPoolQueueDepth={clutchState.shell_pool_queue_depth}
                userAvatar={userAvatar}
                userName={userName}
                terminalLogs={terminalLogs}
                onClearTerminal={handleClearTerminal}
                mentionableAgents={mentionableAgents}
                selectedMentionAgentId={selectedAgentId}
                onMentionAgentChange={syncSelectedAgentFromMention}
                workspacePath={workspace?.workspace_path}
                isHistorySessionView={historySessionViewRunId === sessionRunId}
                onOpenWorkspaceFile={(path) => { void handleOpenWorkspaceFile(path); }}
                onPreviewSnippet={handlePreviewSnippet}
                onViewToolStepInTerminal={handleViewToolStepInTerminal}
                mcpServerIds={selectedAgent?.mcpServerIds}
                showMcpBindingBadge={
                  Boolean(selectedAgent && isClutchAgentType(selectedAgent) && !selectedWorkflowId && !clutchState.workflow_id)
                }
                onOpenMcpBind={() => setView('agents')}
                onSlashCommand={handleSlashCommand}
                slashNotice={slashNotice}
                onDismissSlashNotice={dismissSlashNotice}
                onSelectSession={(session) => { void handleSelectSession(session); }}
              />
              </div>
            </>
        )}

        {/* Right collapsible rail — Coding + Design (Design defaults collapsed) */}
        {(appMode === 'coding' || appMode === 'design') && !['workflows', 'agents', 'tools', 'skills', 'mcp', 'models', 'appearance', 'settings'].includes(currentView) ? (
              <RightPanel
                activeTab={rightTab}
                setActiveTab={setRightTab}
                clutchStatus={clutchStatus}
                activeNodeId={clutchState.active_node_id}
                activeAgent={clutchState.active_agent}
                workflowId={effectiveWorkflowId}
                workflowName={effectiveWorkflowName}
                currentInstruction={clutchState.current_instruction}
                sessionTokens={clutchState.session_tokens}
                sessionCostUsd={clutchState.session_cost_usd}
                tokenInput={clutchState.token_input}
                tokenOutput={clutchState.token_output}
                usageEstimated={clutchState.usage_estimated !== false}
                runStats={clutchState.run_stats}
                uncommitted={uncommitted}
                terminalLogs={terminalLogs}
                isOpen={rightPanelOpen}
                setIsOpen={setRightPanelOpen}
                isMultiAgent={isMultiAgent}
                sessionAgentName={selectedAgentName}
                modelName={footerEffectiveModelName}
                workspaceFiles={workspaceFiles}
                onOpenWorkspaceFile={(path) => { void handleOpenWorkspaceFile(path); }}
                highlightedLogIndex={highlightedLogIndex}
                workspaceAuthorized={Boolean(workspace)}
                onClearTerminal={handleClearTerminal}
                dispatchLog={clutchState.dispatch_log ?? []}
                showTerminalOrchestraOverview={
                  appMode === 'coding'
                  && isPlainLlmFooter
                  && (workspaceViewMode === 'terminal' || sessionHasTerminalHistory(clutchState))
                }
                terminalHistoryReadOnly={
                  appMode === 'coding'
                  && isPlainLlmFooter
                  && isArchivedTerminalHistoryView(clutchState, workspaceViewMode)
                }
                onSelectDispatchEntry={(id) => setHighlightedDispatchEntryId(id)}
                workflowAgentSteps={workflowAgentSteps}
                messages={chatMessages}
              />
        ) : null}
        {/* Unified Settings & Agent Controller Dialog Modal */}
        <SystemPreferencesModal
          currentView={currentView}
          setView={setView}
          isMultiAgent={isMultiAgent}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          activeModelId={activeModelId}
          setActiveModelId={setActiveModelId}
          configuredModels={configuredModels}
          setConfiguredModels={setConfiguredModels}
          themeId={themeId}
          setThemeId={setThemeId}
          workspaceLabel={workspace?.name ?? workspace?.workspace_path?.split('/').pop() ?? null}
          sessionActive={clutchStatus !== 'idle' && clutchStatus !== 'failed'}
          onSelectWorkflow={bindWorkflowForChat}
          onClearSelectedWorkflow={clearWorkflowSelection}
          selectedWorkflowId={selectedWorkflowId}
          activeAgentId={selectedAgentId}
          onActivateAgent={handleActivateAgent}
          userAvatar={userAvatar}
          setUserAvatar={setUserAvatarState}
          userName={userName}
          setUserName={setUserName}
          fontSize={fontSize}
          setFontSize={setFontSize}
          appVersion={appVersion}
          onApplyDefaultWorkspace={(workspaceId) => { void handleSelectWorkspace(workspaceId); }}
          onHighRiskConfirmChange={setHighRiskConfirmEnabled}
        />

      </div>

      {/* 3. Footer Bar Component */}
      <footer 
        style={{ left: `${selectedSidebarWidth}px` }}
        className="@container/footer fixed bottom-0 right-0 h-8 bg-background border-t border-outline-variant flex items-center justify-between gap-2 px-2 @min-[40rem]/footer:px-3 @min-[56rem]/footer:px-4 z-50 text-[11px] text-on-surface-variant/80 select-none transition-all duration-300"
      >
        <div className="flex min-w-0 flex-1 items-center gap-0.5 @min-[48rem]/footer:gap-1 @min-[64rem]/footer:gap-2">
          <div className="relative min-w-0">
            <button
              type="button"
              data-testid="footer-branch-trigger"
              onClick={() => {
                const next = !branchMenuOpen;
                closeFooterMenus();
                setBranchMenuOpen(next);
              }}
              className={`${FOOTER_CHIP_BUTTON_CLASS} text-on-surface-variant`}
              aria-label={`${t('Branch')}: ${workspaceGit.branch || '—'}`}
              title={`${t('Branch')}: ${workspaceGit.branch || '—'}`}
            >
              <LegacyIcon name="account_tree" className="text-[15px] text-on-surface-variant shrink-0" />
              <FooterFieldLabel>{t('Branch')}</FooterFieldLabel>
              <FooterFieldValue>{workspaceGit.branch || '—'}</FooterFieldValue>
              <FooterFieldChevron />
            </button>
            {branchMenuOpen ? (
              <FooterMenuPanel testId="footer-branch-menu">
                {workspaceGit.branches.length === 0 ? (
                  <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{t('Not a git repository')}</p>
                ) : (
                  workspaceGit.branches.map((branch) => (
                    <FooterMenuItem
                      key={branch}
                      testId={`footer-branch-item-${branch}`}
                      selected={branch === workspaceGit.branch}
                      onClick={() => setBranchMenuOpen(false)}
                    >
                      {branch}
                    </FooterMenuItem>
                  ))
                )}
              </FooterMenuPanel>
            ) : null}
          </div>

          {!hideFooterSessionControls ? (
            <>
          {hasWorkflowSelection ? (
            <span
              data-testid="footer-model-disabled"
              className={`${FOOTER_CHIP_CLASS} text-on-surface-variant cursor-default`}
              title={t('Model is determined by the selected workflow')}
            >
              <LegacyIcon name="layers" className="text-[15px] text-on-surface-variant shrink-0" />
              <FooterFieldLabel>{t('Model')}</FooterFieldLabel>
              <FooterFieldValue>—</FooterFieldValue>
            </span>
          ) : showFooterModel ? (
            <div className="relative min-w-0">
              {agentBoundModelId && appMode !== 'design' ? (
                <span
                  data-testid="footer-model-trigger"
                  className={`${FOOTER_CHIP_CLASS} text-on-surface-variant cursor-default`}
                  title={t('Model is bound on this agent')}
                >
                  <LegacyIcon name="layers" className="text-[15px] text-on-surface-variant shrink-0" />
                  <FooterFieldLabel>{t('Model')}</FooterFieldLabel>
                  <FooterFieldValue title={footerEffectiveModelName}>{footerEffectiveModelName}</FooterFieldValue>
                </span>
              ) : (
                <>
              <button
                type="button"
                data-testid="footer-model-trigger"
                onClick={toggleModelMenu}
                className={`${FOOTER_CHIP_BUTTON_CLASS} text-on-surface-variant`}
                aria-label={`${t("Model")}: ${footerEffectiveModelName}`}
                title={`${t("Model")}: ${footerEffectiveModelName}`}
              >
                <LegacyIcon name="layers" className="text-[15px] text-on-surface-variant shrink-0" />
                <FooterFieldLabel>{t('Model')}</FooterFieldLabel>
                <FooterFieldValue title={footerEffectiveModelName}>{footerEffectiveModelName}</FooterFieldValue>
                <FooterFieldChevron />
              </button>
              {modelMenuOpen ? (
                <FooterMenuPanel testId="footer-model-menu">
                  <FooterMenuAction
                    testId="footer-model-manage"
                    onClick={() => {
                      setModelMenuOpen(false);
                      setView('models');
                    }}
                  >
                    {t('Manage models...')}
                  </FooterMenuAction>
                  {configuredModels.length === 0 ? (
                    <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{t('No models configured')}</p>
                  ) : (
                    (() => {
                      const chatModels = configuredModels.filter(
                        (m) => m.available && (m.modelKind ?? 'chat') === 'chat',
                      );
                      const imageModels = configuredModels.filter(
                        (m) => m.available && m.modelKind === 'image',
                      );
                      const videoModels = configuredModels.filter(
                        (m) => m.available && m.modelKind === 'video',
                      );
                      const renderGroup = (
                        label: string,
                        models: typeof configuredModels,
                      ) =>
                        models.length > 0 ? (
                          <React.Fragment key={label}>
                            <FooterMenuSection label={label} />
                            {models.map((model) => (
                              <FooterMenuItem
                                key={model.id}
                                testId={`footer-model-item-${model.id}`}
                                selected={model.id === footerEffectiveModelId}
                                onClick={() => handleFooterModelSelect(model.id)}
                              >
                                {model.name}
                                {modelKindMenuSuffix(model.modelKind)}
                              </FooterMenuItem>
                            ))}
                          </React.Fragment>
                        ) : null;
                      return (
                        <>
                          {renderGroup(t('Chat models'), chatModels)}
                          {renderGroup(t('Image models'), imageModels)}
                          {renderGroup(t('Video models'), videoModels)}
                        </>
                      );
                    })()
                  )}
                </FooterMenuPanel>
              ) : null}
                </>
              )}
            </div>
          ) : !hasWorkflowSelection && customAgentEngineLabel ? (
            <span
              data-testid="footer-engine-label"
              className={`${FOOTER_CHIP_CLASS} text-on-surface-variant cursor-default`}
              title={t('Model is provided by the selected agent tool')}
            >
              <LegacyIcon name="bolt" className="text-[15px] text-on-surface-variant shrink-0" />
              <FooterFieldLabel>{t('Engine')}</FooterFieldLabel>
              <FooterFieldValue title={customAgentEngineLabel}>{customAgentEngineLabel}</FooterFieldValue>
            </span>
          ) : null}

          {isMultiAgent ? (
            <>
              <div className="relative min-w-0">
                {appMode === 'design' ? (
                  <span
                    data-testid="footer-agent-trigger"
                    className={`${FOOTER_CHIP_CLASS} text-on-surface-variant cursor-default opacity-70`}
                    title={t('Design uses the Model LLM, not CLI agents')}
                    aria-label={`${t('Agent')}: ${t('Clutch Agent')}`}
                  >
                    <LegacyIcon name="smart_toy" className="text-[15px] shrink-0" />
                    <FooterFieldLabel>{t('Agent')}</FooterFieldLabel>
                    <FooterFieldValue>{t('Clutch Agent')}</FooterFieldValue>
                  </span>
                ) : (
                  <>
                    <button
                      type="button"
                      data-testid="footer-agent-trigger"
                      onClick={toggleAgentMenu}
                      className={`${FOOTER_CHIP_BUTTON_CLASS} ${
                        selectedAgentId
                          ? 'text-primary font-bold'
                          : 'text-on-surface-variant'
                      }`}
                      aria-label={`${t('Agent')}: ${multiAgentFooterName}`}
                      title={`${t('Agent')}: ${multiAgentFooterName}`}
                    >
                      <LegacyIcon name="smart_toy" className="text-[15px] shrink-0" />
                      <FooterFieldLabel>{t('Agent')}</FooterFieldLabel>
                      <FooterFieldValue title={multiAgentFooterName}>{multiAgentFooterName}</FooterFieldValue>
                      <FooterFieldChevron />
                    </button>
                    {agentMenuOpen ? (
                      <FooterMenuPanel testId="footer-agent-menu">
                        <FooterMenuAction
                          testId="footer-agent-manage"
                          onClick={() => {
                            setAgentMenuOpen(false);
                            setView('agents');
                          }}
                        >
                          {t('Manage agents...')}
                        </FooterMenuAction>
                        {footerSelectableAgents.map((agent) => (
                          <FooterMenuItem
                            key={agent.id}
                            testId={`footer-agent-item-${agent.id}`}
                            selected={agent.id === selectedAgentId}
                            onClick={() => handleFooterAgentSelect(agent)}
                          >
                            {getAgentDisplayName(agent)}
                          </FooterMenuItem>
                        ))}
                      </FooterMenuPanel>
                    ) : null}
                  </>
                )}
              </div>
              <div className={`relative min-w-0 ${footerIdleHiddenClass(!hasWorkflowSelection)}`}>
                {appMode === 'design' ? (
                  <span
                    data-testid="footer-workflow-trigger"
                    className={`${FOOTER_CHIP_CLASS} text-on-surface-variant cursor-default opacity-70`}
                    title={t('Workflows are available in Coding mode')}
                    aria-label={`${t('Workflow')}: —`}
                  >
                    <LegacyIcon name="fork_right" className="text-[15px] shrink-0" />
                    <FooterFieldLabel>{t('Workflow')}</FooterFieldLabel>
                    <FooterFieldValue>—</FooterFieldValue>
                  </span>
                ) : (
                  <>
                    <button
                      type="button"
                      data-testid="footer-workflow-trigger"
                      onClick={() => { void toggleWorkflowMenu(); }}
                      className={`${FOOTER_CHIP_BUTTON_CLASS} ${
                        hasWorkflowSelection
                          ? 'text-primary font-bold'
                          : 'text-on-surface-variant'
                      }`}
                      aria-label={`${t('Workflow')}: ${activeWorkflowLabel}`}
                      title={`${t('Workflow')}: ${activeWorkflowLabel}`}
                    >
                      <LegacyIcon name="fork_right" className="text-[15px] shrink-0" />
                      <FooterFieldLabel>{t('Workflow')}</FooterFieldLabel>
                      <FooterFieldValue title={activeWorkflowLabel}>{activeWorkflowLabel}</FooterFieldValue>
                      <FooterFieldChevron />
                    </button>
                    {workflowMenuOpen ? (
                      <FooterMenuPanel testId="footer-workflow-menu">
                        <FooterMenuAction
                          testId="footer-workflow-manage"
                          onClick={() => {
                            setWorkflowMenuOpen(false);
                            setView('workflows');
                          }}
                        >
                          {t('Manage workflows...')}
                        </FooterMenuAction>
                        {footerWorkflows.length === 0 ? (
                          <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{t('No workflows yet')}</p>
                        ) : (
                          footerWorkflows.map((workflow) => (
                            <FooterMenuItem
                              key={workflow.id}
                              testId={`footer-workflow-item-${workflow.id}`}
                              selected={workflow.id === (selectedWorkflowId || clutchState.workflow_id)}
                              onClick={() => {
                                handleUseWorkflowInChat(workflow.id, workflow.name);
                                setWorkflowMenuOpen(false);
                              }}
                            >
                              {workflow.name}
                            </FooterMenuItem>
                          ))
                        )}
                      </FooterMenuPanel>
                    ) : null}
                  </>
                )}
              </div>
            </>
          ) : appMode === 'design' ? (
            <span
              data-testid="footer-agent-trigger"
              className={`${FOOTER_CHIP_CLASS} text-on-surface-variant cursor-default opacity-70`}
              title={t('Design uses the Model LLM, not CLI agents')}
              aria-label={`${t('Agent')}: ${t('Clutch Agent')}`}
            >
              <LegacyIcon name="smart_toy" className="text-[15px] shrink-0" />
              <FooterFieldLabel>{t('Agent')}</FooterFieldLabel>
              <FooterFieldValue>{t('Clutch Agent')}</FooterFieldValue>
            </span>
          ) : (
            <div className="relative min-w-0">
              <button
                type="button"
                data-testid="footer-agent-trigger"
                onClick={toggleAgentMenu}
                className={`${FOOTER_CHIP_BUTTON_CLASS} text-primary font-bold`}
                aria-label={`${t('Agent')}: ${selectedAgentName}`}
                title={`${t('Agent')}: ${selectedAgentName}`}
              >
                <LegacyIcon name="smart_toy" className="text-[15px] text-primary shrink-0" />
                <FooterFieldLabel>{t('Agent')}</FooterFieldLabel>
                <FooterFieldValue title={selectedAgentName}>{selectedAgentName}</FooterFieldValue>
                <FooterFieldChevron />
              </button>
              {agentMenuOpen ? (
                <FooterMenuPanel testId="footer-agent-menu">
                  <FooterMenuAction
                    testId="footer-agent-manage"
                    onClick={() => {
                      setAgentMenuOpen(false);
                      setView('agents');
                    }}
                  >
                    {t('Manage agents...')}
                  </FooterMenuAction>
                  {footerSelectableAgents.map((agent) => (
                    <FooterMenuItem
                      key={agent.id}
                      testId={`footer-agent-item-${agent.id}`}
                      selected={agent.id === selectedAgentId}
                      onClick={() => handleFooterAgentSelect(agent)}
                    >
                      {getAgentDisplayName(agent)}
                    </FooterMenuItem>
                  ))}
                </FooterMenuPanel>
              ) : null}
            </div>
          )}
            </>
          ) : null}
        </div>

        <div
          className="shrink-0 flex items-center gap-1.5 font-semibold text-on-surface-variant/70 italic pl-1 select-text"
          data-testid="footer-app-brand"
        >
          <BrandLogo
            src={clutchMarkUrl}
            alt=""
            rounded="none"
            className="w-3.5 h-3.5 rounded-sm flex items-center justify-center flex-shrink-0 bg-black"
            imgClassName="w-full h-full object-cover block"
          />
          <span>
            <span className="@max-[32rem]/footer:hidden">Clutch </span>v{appVersion}
          </span>
        </div>
      {promptModal && (
        <PromptModal
          isOpen={promptModal.isOpen}
          title={promptModal.title}
          message={promptModal.message}
          hasInput={promptModal.hasInput}
          placeholder={promptModal.placeholder}
          defaultValue={promptModal.defaultValue}
          onConfirm={promptModal.onConfirm}
          onCancel={() => setPromptModal(null)}
        />
      )}
      </footer>
      {previewToast ? (
        <div
          className="fixed bottom-16 left-1/2 -translate-x-1/2 z-[80] max-w-md px-4 py-2 rounded-xl bg-neutral-900 text-white text-[12px] font-medium shadow-xl"
          role="status"
        >
          {previewToast}
        </div>
      ) : null}
    </div>
  );
}


export default function App() {
  if (import.meta.env.DEV && new URLSearchParams(window.location.search).get('dev_tools_empty') === '1') {
    return (
      <LanguageProvider>
        <DevOnboardingToolsEmptyPreview />
      </LanguageProvider>
    );
  }

  return (
    <LanguageProvider>
      <AppErrorBoundary>
        <AppGate />
      </AppErrorBoundary>
    </LanguageProvider>
  );
}


function AppGate() {
  const [onboardingCompleted, setOnboardingCompleted] = useState<boolean | null>(null);

  useEffect(() => {
    void fetchOnboardingState()
      .then((done) => setOnboardingCompleted(done))
      .catch(() => setOnboardingCompleted(false));
  }, []);

  if (onboardingCompleted === null) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-on-surface-variant text-sm font-sans">
        …
      </div>
    );
  }

  if (!onboardingCompleted) {
    return (
      <OnboardingWizard
        onComplete={() => {
          setOnboardingCompleted(true);
        }}
      />
    );
  }

  return <MainLayout />;
}
