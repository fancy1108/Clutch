import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './sidebar';
import { ChatFeed, configuredEngineToRuntimeLabel } from './components/ChatFeed';
import { RightPanel } from './components/RightPanel';
import { WorkflowOrchestration } from './components/WorkflowOrchestration';
import { AgentManager } from './components/AgentManager';
import AiToolsManager from './components/AiToolsManager';
import { SkillsRegistry } from './components/SkillsRegistry';
import { McpServerHub } from './components/McpServerHub';
import { ModelsManager } from './components/ModelsManager';
import { ThemeManager, THEME_PRESETS } from './components/ThemeManager';
import { SystemPreferencesModal } from './components/SystemPreferencesModal';
import { FooterMenuAction, FooterMenuItem, FooterMenuPanel } from './components/FooterMenu';
import { MainView, RightTab, ChatMessage, UncommittedFile, DiffLine, type Agent, type ClutchState } from './types';
import { fetchAgents } from './services/agentApi';
import {
  BUILTIN_AGENT_ID,
  getAgentDisplayName,
  isBuiltinAgent,
  mergeAgentsWithBuiltin,
} from './services/builtinAgent';
import { fetchPreferences, saveThemePreference, saveUserNamePreference, type ThemePresetId } from './services/themeApi';
import { LanguageProvider, useLanguage } from './components/LanguageContext';
import { clutchStore, createSessionRunId, submitChatMessage, useClutchState, setUserChatAvatar } from './services/clutchState';
import { fetchSessions, createSession, startWorkflowRun, fetchRunState, deleteSession, type SessionRecord } from './services/runApi';
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
import { isClutchAgentType, agentTypeFromAgent, agentTypeLabel } from './services/agentTypes';
import { resolveAgentBrandLogo, resolveBrandLogoSrc } from './services/brandLogos';
import {
  activateWorkspace,
  addWorkspace,
  removeWorkspace,
  fetchWorkspaceFile,
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
import { pickWorkspaceFolder } from './services/pickWorkspaceFolder';
import { fetchModelsConfig, mapModelConfigToUi, saveModelsConfig } from './services/modelsApi';
import { fetchPermissionMode, savePermissionMode, type PermissionMode } from './services/permissionApi';
import { fetchSkillsRegistry, type ScannedSkill } from './services/skillsApi';
import { BTN_GHOST, BTN_PRIMARY } from './components/ui/buttonStyles';
import { LegacyIcon } from './components/ui/LegacyIcon';
import { isTauri } from '@tauri-apps/api/core';
import { getVersion } from '@tauri-apps/api/app';

function MainLayout() {
  const { t } = useLanguage();
  const { state: clutchState } = useClutchState();
  const [appVersion, setAppVersion] = useState<string>('0.1.0');

  useEffect(() => {
    if (isTauri()) {
      getVersion()
        .then((v) => setAppVersion(v))
        .catch((err) => console.warn('[Clutch] Failed to fetch app version:', err));
    }
  }, []);

  const [sessionRunId, setSessionRunId] = useState(() => createSessionRunId());

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
  const chatMessages = clutchState.messages as ChatMessage[];
  const terminalLogs = clutchState.terminal_logs;

  // Navigation & Structure views
  const [currentView, setView] = useState<MainView>('chat');
  const [currentFlowName, setCurrentFlowName] = useState<string>('');
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const [workflowAgentSteps, setWorkflowAgentSteps] = useState<WorkflowAgentStep[]>([]);
  const [isMultiAgent, setIsMultiAgent] = useState<boolean>(true);
  const [themeId, setThemeIdState] = useState<ThemePresetId>('pristine-light');
  const [userAvatar, setUserAvatarState] = useState<string>('');
  const [userName, setUserNameState] = useState<string>('User');

  useEffect(() => {
    void fetchPreferences()
      .then((prefs) => {
        setThemeIdState(prefs.active_theme_id);
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

  const setThemeId = (id: string) => {
    const preset = THEME_PRESETS.find((item) => item.id === id);
    if (!preset) return;
    setThemeIdState(preset.id as ThemePresetId);
    void saveThemePreference(preset.id as ThemePresetId).catch(() => {});
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
    contextWindow: string;
    temperature: number;
    sourceSummary: string;
    credentialSourceLabel: string | null;
  }>>([]);

  // Column Collapsing states
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [rightPanelOpen, setRightPanelOpen] = useState<boolean>(true);

  // File Preview state
  const [previewFile, setPreviewFile] = useState<{ name: string; content: string } | null>(null);

  // Repository list folders state
  const [folders, setFolders] = useState<import('./types').RepositoryFolder[]>([]);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [shellSnapshotRunIds, setShellSnapshotRunIds] = useState<ReadonlySet<string>>(() => new Set());
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [repositoryGroups, setRepositoryGroups] = useState<RepositoryGroup[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [workspaceFiles, setWorkspaceFiles] = useState<FileTreeNode[]>([]);
  const [workspacePickError, setWorkspacePickError] = useState<string | null>(null);
  const [highRiskConfirmed, setHighRiskConfirmed] = useState(false);

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
  const [configuredAgents, setConfiguredAgents] = useState<Agent[]>([]);

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
        setWorkspaces(listed.workspaces);
        setActiveWorkspaceId(listed.active_id);
        const active = listed.workspaces.find((item) => item.id === listed.active_id) ?? null;
        setWorkspace(active);
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
    if (isMultiAgent) clearWorkflowSelection();
  };

  const selectedAgent = configuredAgents.find((agent) => agent.id === selectedAgentId);
  const selectedAgentName = getAgentDisplayName(selectedAgent);
  const activeWorkflowLabel = clutchState.workflow_id || currentFlowName || selectedWorkflowId || '—';
  const hasWorkflowSelection = isMultiAgent && activeWorkflowLabel !== '—';
  const multiAgentFooterName = hasWorkflowSelection
    ? '—'
    : selectedAgentId
      ? selectedAgentName
      : '—';
  const showFooterModel =
    !hasWorkflowSelection && isClutchAgentType(selectedAgent);
  const agentBoundModelId =
    selectedAgent && !isBuiltinAgent(selectedAgent) && selectedAgent.modelId
      ? selectedAgent.modelId
      : undefined;
  const footerEffectiveModelId = agentBoundModelId || activeModelId;
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

  const refreshSessions = async () => {
    try {
      const [runs, snapshots] = await Promise.all([
        fetchSessions(),
        fetchShellSnapshots().catch(() => []),
      ]);
      setSessions(runs);
      setShellSnapshotRunIds(new Set(snapshots.map((snap) => snap.run_id)));
    } catch (error: unknown) {
      console.warn('[Clutch] sessions unavailable:', error);
    }
  };

  useEffect(() => {
    void refreshSessions();
  }, [clutchState.run_id, clutchState.status, activeWorkspaceId]);

  // Active Tab inside the right side panel (Overview, Files, Flow, Changes, Terminal)
  const [rightTab, setRightTab] = useState<RightTab>('overview');

  const prevClutchStatusRef = useRef(clutchStatus);

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
  const selectedSidebarWidth = sidebarOpen ? 280 : 0;
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
    if (!isMultiAgent && rightTab === 'flow') {
      setRightTab('overview');
    }
    if (!effectiveWorkflowId && rightTab === 'flow') {
      setRightTab('overview');
    }
  }, [isMultiAgent, rightTab, effectiveWorkflowId]);

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

  const handleStopRun = () => {
    // Workflow (Flow) runs: stop immediately without confirmation.
    // Plain LLM chat runs: ask once to avoid accidental interruption.
    if (!isWorkflowChat && !highRiskConfirmed) {
      const ok = window.confirm(t('Confirm stopping the current run? This will interrupt Builder/Evaluator execution.'));
      if (!ok) return;
      setHighRiskConfirmed(true);
    }
    void clutchStore.send({ action: 'stop_run' });
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
      const content = await fetchWorkspaceFile(path);
      setPreviewFile({ name: path, content });
    } catch (error) {
      console.error('[Clutch] read file failed:', error);
    }
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

  // Chat Input Box State
  const [inputValue, setInputValue] = useState<string>('');

  // Permission mode (persisted on backend)
  const [permissionMode, setPermissionMode] = useState<PermissionMode>('ask');

  useEffect(() => {
    void fetchPermissionMode()
      .then((mode) => setPermissionMode(mode))
      .catch(() => {});
  }, []);

  const handlePermissionModeChange = (mode: PermissionMode) => {
    setPermissionMode(mode);
    void savePermissionMode(mode).catch(() => {});
  };

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

  const handleNewChat = async () => {
    if (!workspace) {
      await handlePickWorkspace();
      return;
    }
    scheduleBackgroundHydrateForRun(sessionRunId);
    const runId = createSessionRunId();
    setSessionRunId(runId);
    setCurrentFlowName('');
    setSelectedWorkflowId(null);
    selectDefaultAgent();
    setView('chat');
    setRightTab('overview');
    void clutchStore.connect(runId);
  };

  const handleSelectSession = async (session: SessionRecord) => {
    if (session.workspace_id && session.workspace_id !== activeWorkspaceId) {
      await handleSelectWorkspace(session.workspace_id);
    }
    if (session.run_id !== sessionRunId) {
      scheduleBackgroundHydrateForRun(sessionRunId);
    }
    let hydratedState: ClutchState | null = null;
    try {
      const { state } = await fetchRunState(session.run_id);
      hydratedState = state;
      clutchStore.setPendingHydrate(state);
    } catch (error) {
      console.warn('[Clutch] session state hydrate failed:', error);
    }
    setSessionRunId(session.run_id);

    const storedMode = localStorage.getItem(`clutch_session_mode_${session.run_id}`);
    const storedFlowId = localStorage.getItem(`clutch_session_flow_${session.run_id}`);
    const storedAgentId = localStorage.getItem(`clutch_session_agent_${session.run_id}`);

    setIsMultiAgent(true);

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

    setView('chat');
  };

  const handleNewChatInWorkspace = async (workspaceId: string) => {
    if (workspaceId !== activeWorkspaceId) {
      await handleSelectWorkspace(workspaceId);
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
          const updatedSessions = await fetchSessions();
          setSessions(updatedSessions);

          if (sessionRunId === runId) {
            const remainingWorkspaceSessions = updatedSessions.filter(
              (s) => s.workspace_id === activeWorkspaceId && s.run_id !== runId
            );

            if (remainingWorkspaceSessions.length > 0) {
              await handleSelectSession(remainingWorkspaceSessions[0]);
            } else {
              const tempRunId = createSessionRunId();
              setSessionRunId(tempRunId);
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
      const mentionAgentId = resolveWorkflowMentionAgentId(
        text,
        workflowAgentSteps,
        configuredAgents,
      );
      await submitChatMessage(text, mentionAgentId ?? clutchState.refine_agent_id ?? undefined);
      await refreshSessions();
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
      clutchStore.optimisticWorkflowStart({
        runId: sessionRunId,
        workflowId,
        instruction,
        activeAgent: workflowAgentSteps[0]?.agentName || undefined,
      });
      try {
        try {
          await createSession({
            run_id: sessionRunId,
            title: instruction.slice(0, 80) || t('New session'),
            workflow_id: workflowId,
          });
        } catch {
          // session may already exist for this run_id
        }
        if (!clutchStore.connected) {
          await clutchStore.connect(sessionRunId);
        }
        await refreshSessions();
        // Optimistically mark this session as running so the sidebar spinner
        // stays visible when the user switches to another session while the
        // workflow is still executing (startWorkflowRun is a blocking HTTP call).
        setSessions(prev =>
          prev.map(s => s.run_id === sessionRunId ? { ...s, status: 'running' } : s)
        );
        const result = await startWorkflowRun(sessionRunId, workflowId, instruction);
        clutchStore.mergeWorkflowComplete(result.state);
        setSelectedWorkflowId(null);
        await refreshSessions();
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to start workflow';
        setWorkspacePickError(message);
        clutchStore.replaceState({
          ...clutchStore.getSnapshot(),
          status: 'failed',
        });
        console.error('[Clutch] workflow start failed:', error);
      }
      return;
    }
    const clientMessageId = clutchStore.optimisticPlainChatSend(text.trim());
    await submitChatMessage(
      text,
      selectedAgentId,
      agentBoundModelId ? undefined : footerEffectiveModelId || undefined,
      clientMessageId,
    );
    await refreshSessions();
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
      className="relative h-screen max-h-screen bg-background text-on-surface overflow-hidden flex flex-col font-sans select-none"
    >
      
      {/* 1. Header component */}
      <Header
        currentFlow={currentFlowName || clutchState.workflow_id || t('New session')}
        workspaceName={workspace?.name}
        onPickWorkspace={() => { void handlePickWorkspace(); }}
        folders={folders}
        isMultiAgent={isMultiAgent}
        setIsMultiAgent={handleSetIsMultiAgent}
        onGoBack={handleClearSessionView}
        setView={setView}
        sidebarOpen={sidebarOpen}
        selectedModel={selectedModel}
      />

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
          onNewChat={() => { void handleNewChat(); }}
          isOpenState={sidebarOpen}
          setIsOpenState={setSidebarOpen}
          isMultiAgent={isMultiAgent}
          sessions={sessions}
          shellSnapshotRunIds={shellSnapshotRunIds}
          activeSessionId={sessionRunId}
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

        {/* Central screen switcher with Right component based on Left tab selections */}
        {true && (
          previewFile ? (
            <div 
              style={{ paddingLeft: `${selectedSidebarWidth}px`, paddingTop: '64px' }}
              className="flex-1 flex flex-col bg-white h-screen overflow-hidden animate-fade-in relative z-30 transition-all duration-300"
            >
              {/* File Preview Header */}
              <div className="h-14 border-b border-outline-variant/60 flex items-center justify-between px-6 bg-neutral-50/50 flex-shrink-0 select-none">
                <div className="flex items-center gap-3">
                  <LegacyIcon
                    name={previewFile.name.endsWith('.md') ? 'markdown' : 'code'}
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

                <button
                  onClick={() => setPreviewFile(null)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-neutral-500 hover:text-neutral-900 hover:bg-neutral-200/50 rounded-lg text-[11px] font-semibold transition-colors"
                >
                  <LegacyIcon name="close" className="text-[16px]" />
                  Close
                </button>
              </div>

              {/* Code/Markdown Content Viewer */}
              <div className="flex-1 overflow-y-auto p-8 font-mono text-xs text-neutral-800 bg-[#f9f9f9] select-text leading-relaxed">
                {previewFile.name.endsWith('.md') ? (
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
          ) : (
            <>
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
                onStopRun={handleStopRun}
                isMultiAgent={isMultiAgent}
                onApprove={handleApprove}
                onReject={handleReject}
                onRetryWithInstructions={handleRetryWithInstructions}
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
                llmModelName={selectedModel}
                activeAgentName={chatActiveAgentName}
                activeAgentAvatar={chatActiveAgentAvatar}
                activeNodeId={clutchState.active_node_id}
                workflowAgentSteps={workflowAgentSteps}
                resolveAgentLogo={resolveAgentLogo}
                engineHint={runtimeEngineHint}
                workspaceFiles={workspaceFiles}
                sessions={sessions}
                skills={chatSkills}
                permissionMode={permissionMode}
                onPermissionModeChange={handlePermissionModeChange}
                shellSessionStatus={clutchState.shell_session_status}
                userAvatar={userAvatar}
                userName={userName}
              />
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
                uncommitted={uncommitted}
                terminalLogs={terminalLogs}
                isOpen={rightPanelOpen}
                setIsOpen={setRightPanelOpen}
                isMultiAgent={isMultiAgent}
                sessionAgentName={selectedAgentName}
                modelName={footerEffectiveModelName}
                workspaceFiles={workspaceFiles}
                onOpenWorkspaceFile={(path) => { void handleOpenWorkspaceFile(path); }}
                workspaceAuthorized={Boolean(workspace)}
                onClearTerminal={handleClearTerminal}
              />
            </>
          )
        )}

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
          onUseWorkflowInChat={handleUseWorkflowInChat}
          onSelectWorkflow={bindWorkflowForChat}
          onClearSelectedWorkflow={clearWorkflowSelection}
          selectedWorkflowId={selectedWorkflowId}
          activeAgentId={selectedAgentId}
          onActivateAgent={handleActivateAgent}
          userAvatar={userAvatar}
          setUserAvatar={setUserAvatarState}
          userName={userName}
          setUserName={setUserName}
        />

      </div>

      {/* 3. Footer Bar Component */}
      <footer 
        style={{ left: `${selectedSidebarWidth}px` }}
        className="fixed bottom-0 right-0 h-8 bg-background border-t border-outline-variant flex items-center justify-between px-6 z-50 text-[11px] text-on-surface-variant/80 select-none transition-all duration-300"
      >
        <div className="flex items-center gap-6">
          <div className="relative">
            <button
              type="button"
              data-testid="footer-branch-trigger"
              onClick={() => {
                const next = !branchMenuOpen;
                closeFooterMenus();
                setBranchMenuOpen(next);
              }}
              className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer font-medium whitespace-nowrap"
              aria-label={`${t('Branch')}: ${workspaceGit.branch || '—'}`}
            >
              <LegacyIcon name="fork_right" className="text-[15px] text-on-surface-variant" />
              {t('Branch')}: {workspaceGit.branch || '—'}
              <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
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

          {!hasWorkflowSelection && showFooterModel ? (
            <div className="relative">
              {agentBoundModelId ? (
                <span
                  data-testid="footer-model-trigger"
                  className="flex items-center gap-1.5 px-2 py-1 rounded font-medium text-on-surface-variant whitespace-nowrap cursor-default"
                  title={t('Model is bound on this agent')}
                >
                  <LegacyIcon name="layers" className="text-[15px] text-on-surface-variant" />
                  {t("Model")}: {footerEffectiveModelName}
                </span>
              ) : (
                <>
              <button
                type="button"
                data-testid="footer-model-trigger"
                onClick={toggleModelMenu}
                className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low hover:text-on-surface transition-colors cursor-pointer font-medium text-on-surface-variant whitespace-nowrap"
                aria-label={`${t("Model")}: ${footerEffectiveModelName}`}
              >
                <LegacyIcon name="layers" className="text-[15px] text-on-surface-variant" />
                {t("Model")}: {footerEffectiveModelName}
                <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
              </button>
              {modelMenuOpen ? (
                <FooterMenuPanel testId="footer-model-menu">
                  {configuredModels.length === 0 ? (
                    <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{t('No models configured')}</p>
                  ) : (
                    configuredModels.map((model) => (
                      <FooterMenuItem
                        key={model.id}
                        testId={`footer-model-item-${model.id}`}
                        selected={model.id === footerEffectiveModelId}
                        onClick={() => handleFooterModelSelect(model.id)}
                      >
                        {model.name}
                      </FooterMenuItem>
                    ))
                  )}
                  <FooterMenuAction
                    testId="footer-model-manage"
                    onClick={() => {
                      setModelMenuOpen(false);
                      setView('models');
                    }}
                  >
                    {t('Manage models...')}
                  </FooterMenuAction>
                </FooterMenuPanel>
              ) : null}
                </>
              )}
            </div>
          ) : !hasWorkflowSelection && customAgentEngineLabel ? (
            <span
              data-testid="footer-engine-label"
              className="flex items-center gap-1.5 px-2 py-1 rounded font-medium text-on-surface-variant cursor-default whitespace-nowrap"
              title={t('Model is provided by the selected agent tool')}
            >
              <LegacyIcon name="bolt" className="text-[15px] text-on-surface-variant" />
              {t('Engine')}: {customAgentEngineLabel}
            </span>
          ) : null}

          {isMultiAgent ? (
            <>
              {!hasWorkflowSelection ? (
              <div className="relative">
                <button
                  type="button"
                  data-testid="footer-agent-trigger"
                  onClick={toggleAgentMenu}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low transition-colors cursor-pointer font-medium whitespace-nowrap ${
                    selectedAgentId
                      ? 'text-primary font-bold'
                      : 'text-on-surface-variant'
                  }`}
                  aria-label={`${t('Active Agent')}: ${multiAgentFooterName}`}
                >
                  <LegacyIcon name="smart_toy" className="text-[15px]" />
                  {t('Active Agent')}: {multiAgentFooterName}
                  <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
                </button>
                {agentMenuOpen ? (
                  <FooterMenuPanel testId="footer-agent-menu">
                    {configuredAgents.map((agent) => (
                      <FooterMenuItem
                        key={agent.id}
                        testId={`footer-agent-item-${agent.id}`}
                        selected={agent.id === selectedAgentId}
                        onClick={() => handleFooterAgentSelect(agent)}
                      >
                        {getAgentDisplayName(agent)}
                      </FooterMenuItem>
                    ))}
                    <FooterMenuAction
                      testId="footer-agent-manage"
                      onClick={() => {
                        setAgentMenuOpen(false);
                        setView('agents');
                      }}
                    >
                      {t('Manage agents...')}
                    </FooterMenuAction>
                  </FooterMenuPanel>
                ) : null}
              </div>
              ) : null}
              <div className="relative">
                <button
                  type="button"
                  data-testid="footer-workflow-trigger"
                  onClick={() => { void toggleWorkflowMenu(); }}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low transition-colors cursor-pointer font-medium whitespace-nowrap ${
                    hasWorkflowSelection
                      ? 'text-primary font-bold'
                      : 'text-on-surface-variant'
                  }`}
                  aria-label={`${t('Workflow')}: ${activeWorkflowLabel}`}
                >
                  <LegacyIcon name="account_tree" className="text-[15px]" />
                  {t('Workflow')}: {activeWorkflowLabel}
                  <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
                </button>
                {workflowMenuOpen ? (
                  <FooterMenuPanel testId="footer-workflow-menu">
                    {footerWorkflows.length === 0 ? (
                      <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{t('No workflows yet')}</p>
                    ) : (
                      footerWorkflows.map((workflow) => (
                        <FooterMenuItem
                          key={workflow.id}
                          testId={`footer-workflow-item-${workflow.id}`}
                          selected={workflow.id === (selectedWorkflowId || clutchState.workflow_id)}
                          onClick={() => {
                            bindWorkflowForChat(workflow.id, workflow.name);
                            setWorkflowMenuOpen(false);
                          }}
                        >
                          {workflow.name}
                        </FooterMenuItem>
                      ))
                    )}
                    <FooterMenuAction
                      testId="footer-workflow-manage"
                      onClick={() => {
                        setWorkflowMenuOpen(false);
                        setView('workflows');
                      }}
                    >
                      {t('Manage workflows...')}
                    </FooterMenuAction>
                  </FooterMenuPanel>
                ) : null}
              </div>
            </>
          ) : (
            <div className="relative">
              <button
                type="button"
                data-testid="footer-agent-trigger"
                onClick={toggleAgentMenu}
                className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-surface-container-low text-primary font-bold transition-colors cursor-pointer whitespace-nowrap"
                aria-label={`${t("Active Agent")}: ${selectedAgentName}`}
              >
                <LegacyIcon name="smart_toy" className="text-[15px] text-primary" />
                {t("Active Agent")}: {selectedAgentName}
                <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
              </button>
              {agentMenuOpen ? (
                <FooterMenuPanel testId="footer-agent-menu">
                  {configuredAgents.map((agent) => (
                    <FooterMenuItem
                      key={agent.id}
                      testId={`footer-agent-item-${agent.id}`}
                      selected={agent.id === selectedAgentId}
                      onClick={() => handleFooterAgentSelect(agent)}
                    >
                      {getAgentDisplayName(agent)}
                    </FooterMenuItem>
                  ))}
                  <FooterMenuAction
                    testId="footer-agent-manage"
                    onClick={() => {
                      setAgentMenuOpen(false);
                      setView('agents');
                    }}
                  >
                    {t('Manage agents...')}
                  </FooterMenuAction>
                </FooterMenuPanel>
              ) : null}
            </div>
          )}
        </div>

        <div className="font-semibold text-on-surface-variant/70 italic mr-2 select-text">
          Clutch v{appVersion}
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
    </div>
  );
}

interface PromptModalProps {
  isOpen: boolean;
  title: string;
  message?: string;
  hasInput?: boolean;
  placeholder?: string;
  defaultValue?: string;
  onConfirm: (value: string) => void;
  onCancel: () => void;
}

const PromptModal: React.FC<PromptModalProps> = ({
  isOpen,
  title,
  message = '',
  hasInput = false,
  placeholder = '',
  defaultValue = '',
  onConfirm,
  onCancel,
}) => {
  const [value, setValue] = useState(defaultValue);
  const { t } = useLanguage();

  useEffect(() => {
    if (isOpen) {
      setValue(defaultValue);
    }
  }, [isOpen, defaultValue]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-[2px] flex items-center justify-center z-[1000] select-none">
      <div className="bg-surface-bright border border-outline-variant w-full max-w-sm rounded-xl shadow-xl p-4 space-y-3">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-on-surface">{title}</h3>
        
        {message && (
          <p className="text-[13px] text-on-surface-variant leading-relaxed select-text">
            {message}
          </p>
        )}

        {hasInput && (
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
            className="w-full rounded-lg border border-outline-variant/60 bg-surface px-2.5 py-1.5 text-[11px] text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary/50"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                onConfirm(value);
              } else if (e.key === 'Escape') {
                onCancel();
              }
            }}
          />
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onCancel} className={BTN_GHOST}>
            {t('Cancel')}
          </button>
          <button type="button" onClick={() => onConfirm(value)} className={BTN_PRIMARY}>
            {t('Confirm')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <LanguageProvider>
      <MainLayout />
    </LanguageProvider>
  );
}
