
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { isTauri } from '@tauri-apps/api/core';
import { getVersion } from '@tauri-apps/api/app';
import { configuredEngineToRuntimeLabel } from '../components/ChatFeed';
import { getDesignSession } from '../services/designApi';
import { fetchAgents } from '../services/agentApi';
import {
  BUILTIN_AGENT_ID,
  getAgentDisplayName,
  isBuiltinAgent,
  mergeAgentsWithBuiltin,
} from '../services/builtinAgent';
import {
  clutchStore,
  createSessionRunId,
  submitChatMessage,
  useClutchState,
  clearWorkflowForSession,
} from '../services/clutchState';
import {
  compactRun,
  createSession,
  deleteSession,
  fetchRunState,
  fetchSessions,
  resolveSessionHistoryWorkspaceId,
  startWorkflowRun,
  type SessionRecord,
} from '../services/runApi';
import type { SlashCommandId } from '../services/slashCommands';
import { fetchShellSnapshots } from '../services/shellSnapshotApi';
import { listWorkflowItems, loadWorkflowById } from '../services/workflowApi';
import {
  findWorkflowStep,
  isWorkflowSystemAgent,
  orderedWorkflowAgentSteps,
  resolveInProgressWorkflowStep,
  resolveWorkflowMentionAgentId,
  shouldRouteWorkflowRefine,
  type WorkflowAgentStep,
} from '../services/workflowAgentSteps';
import { agentTypeFromAgent, agentTypeLabel, isCliAgentType, isClutchAgentType } from '../services/agentTypes';
import {
  filterAgentsForTerminalWorkspace,
  filterCliAgents,
  loadWorkspaceViewMode,
  resolveDefaultTerminalAgent,
  saveWorkspaceViewMode,
  type WorkspaceViewMode,
} from '../services/workspaceViewMode';
import {
  CLI_DISPLAY,
  formatInputMention,
  isArchivedTerminalHistoryView,
  normalizeTerminalSessionForResume,
  saveLastCliAgentId,
  sessionHasPersistableContent,
  sessionHasTerminalHistory,
  shouldConfirmLeavingTerminal,
  shouldConfirmLeavingTerminalForNewChat,
} from '../services/terminalOrchestraUtils';
import { resolveAgentBrandLogo, resolveBrandLogoSrc } from '../services/brandLogos';
import { fetchModelsConfig, resolveDefaultTextModelId, saveModelsConfig } from '../services/modelsApi';
import { fetchSkillsRegistry, type ScannedSkill } from '../services/skillsApi';
import { resolveChatTerminalSyncTarget } from '../services/chatTerminalSync';
import { SIDEBAR_COLLAPSED_WIDTH_PX, SIDEBAR_EXPANDED_WIDTH_PX } from '../constants/layout';
import type {
  Agent,
  AppWorkspaceMode,
  ChatMessage,
  ClutchState,
  DiffLine,
  MainView,
  RightTab,
  ToolStep,
  UncommittedFile,
} from '../types';
import type { AppPromptModalState } from './useAppWorkspace';
import type { useAppSettings } from './useAppSettings';
import type { useAppWorkspace } from './useAppWorkspace';

type InFlightTurnContext = {
  agentId: string | null;
  agentName: string;
  modelId: string | null;
  modelName: string;
  engineHint: string;
};

type AppSettingsSlice = ReturnType<typeof useAppSettings>;
type AppWorkspaceSlice = ReturnType<typeof useAppWorkspace>;

type UseAppSessionOptions = {
  t: (key: string) => string;
  settings: AppSettingsSlice;
  workspace: AppWorkspaceSlice;
  setPromptModal: (modal: AppPromptModalState | null) => void;
  setView: React.Dispatch<React.SetStateAction<MainView>>;
  currentView: MainView;
};

export function useAppSession({
  t,
  settings,
  workspace: ws,
  setPromptModal,
  setView,
  currentView,
}: UseAppSessionOptions) {
  const {
    activeModelId,
    configuredModels,
    handlePermissionModeChange,
    modelMenuOpen,
    setModelMenuOpen,
    selectedModel,
    syncModelsConfig,
  } = settings;

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
  const chatMessages = clutchState.messages as ChatMessage[];
  const terminalLogs = clutchState.terminal_logs;

  const [appMode, setAppMode] = useState<AppWorkspaceMode>('coding');
const [currentFlowName, setCurrentFlowName] = useState<string>('');
const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
const [workflowAgentSteps, setWorkflowAgentSteps] = useState<WorkflowAgentStep[]>([]);
const [isMultiAgent, setIsMultiAgent] = useState<boolean>(true);

// Active selected model state

// Column Collapsing states
const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
const [rightPanelOpen, setRightPanelOpen] = useState<boolean>(true);

// File Preview state

// Repository list folders state
const [folders, setFolders] = useState<import('./types').RepositoryFolder[]>([]);
const [sessions, setSessions] = useState<SessionRecord[]>([]);
const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
const [historySessionViewRunId, setHistorySessionViewRunId] = useState<string | null>(null);
const [shellSnapshotRunIds, setShellSnapshotRunIds] = useState<ReadonlySet<string>>(() => new Set());
const [highRiskConfirmed, setHighRiskConfirmed] = useState(false);

// Reset high-risk confirmation when switching sessions
useEffect(() => {
  setHighRiskConfirmed(false);
  }, [sessionRunId]);
  const [branchMenuOpen, setBranchMenuOpen] = useState(false);
  const [agentMenuOpen, setAgentMenuOpen] = useState(false);
const [workflowMenuOpen, setWorkflowMenuOpen] = useState(false);
const [footerWorkflows, setFooterWorkflows] = useState<Array<{ id: string; name: string }>>([]);

const closeFooterMenus = useCallback(() => {
  setBranchMenuOpen(false);
  setModelMenuOpen(false);
  setAgentMenuOpen(false);
  setWorkflowMenuOpen(false);
}, [setModelMenuOpen]);
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
 * Stay in Chat mode: do NOT flip the center ws.workspace to interactive Terminal mode
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
    // Sidebar shows every project — never scope to ws.activeWorkspaceId.
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
  if (!ws.workspace) return;
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
}, [ws.workspace, clutchState.workflow_id, t, appMode]);

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
  const prev = prevClutchStatusRef.current;
  prevClutchStatusRef.current = clutchStatus;
  if (prev !== 'running' || clutchStatus === 'running' || !ws.workspace) return;
  void ws.refreshWorkspaceFiles();
  void refreshSessions();
}, [clutchStatus, ws.workspace, ws.refreshWorkspaceFiles]);

useEffect(() => {
  if (rightTab !== 'files' || !ws.workspace) return;
  void ws.refreshWorkspaceFiles();
}, [rightTab, ws.workspace?.id, ws.refreshWorkspaceFiles]);


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

useEffect(() => {
  const handler = (event: Event) => {
    const data = (event as CustomEvent).detail as { path?: string; diff_lines?: DiffLine[] };
    if (!data.path) return;
    setUncommitted((prev) => [
      ...prev.filter((file) => file.name !== data.path),
      { name: data.path, status: 'M', diffs: data.diff_lines || [], active: true },
    ]);
    void ws.refreshWorkspaceFiles();
    setRightTab('changes');
  };
  window.addEventListener('clutch-file-changed', handler);
  return () => window.removeEventListener('clutch-file-changed', handler);
}, [ws.refreshWorkspaceFiles]);

// Close unified settings dialog on ESC key
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      setView(prev => (prev === 'agents' || prev === 'settings' || prev === 'tools' || prev === 'workflows' || prev === 'skills' || prev === 'mcp' || prev === 'models' || prev === 'appearance') ? 'chat' : prev);
    }
  };
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, [setView]);

const handleClearTerminal = () => {
  clutchStore.clearTerminalLogs();
};

const handleStopRun = (): boolean => {
  // Workflow (Flow) runs: stop immediately without confirmation.
  // Plain LLM chat runs: ask once to avoid accidental interruption.
  if (!isWorkflowChat && !highRiskConfirmed) {
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


const toggleAgentMenu = () => {
  const next = !agentMenuOpen;
  closeFooterMenus();
  setAgentMenuOpen(next);
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
  if (!ws.workspace) {
    await ws.handlePickWorkspace();
    return;
  }
  const startNewChat = async () => {
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
    setView('chat');
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
  if (!ws.workspace) {
    await ws.handlePickWorkspace();
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
      void ws.refreshWorkspaceFiles();
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
  [sessionRunId, currentFlowName, t, ws.refreshWorkspaceFiles],
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
        const inActive = codingSessions.filter((s) => s.workspace_id === ws.activeWorkspaceId);
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
    if (session.workspace_id && session.workspace_id !== ws.activeWorkspaceId) {
      await ws.handleSelectWorkspace(session.workspace_id);
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
  if (workspaceId !== ws.activeWorkspaceId) {
    await ws.handleSelectWorkspace(workspaceId);
  }
  if (appMode === 'design') {
    await handleNewDesign();
    return;
  }
  await handleNewChat();
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
            (s) => s.workspace_id === ws.activeWorkspaceId && s.run_id !== runId
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
  if (!ws.workspace) {
    ws.setWorkspacePickError(t('Select a project before starting a conversation.'));
    return;
  }
  if (
    clutchState.workflow_id
    && shouldRouteWorkflowRefine(clutchState.status, clutchState.workflow_id, text)
  ) {
    ws.setWorkspacePickError(null);
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
      ws.setWorkspacePickError(t('Select an AI Agent before sending.'));
      setView('agents');
      return;
    }
  } else {
    const hasWorkflow = Boolean(
      (selectedWorkflowId && !clutchState.workflow_id) || clutchState.workflow_id,
    );
    if (!hasWorkflow && !selectedAgentId) {
      ws.setWorkspacePickError(t('Select an AI Agent or a Workflow before sending.'));
      return;
    }
  }
  if (selectedWorkflowId && !clutchState.workflow_id) {
    const workflowId = selectedWorkflowId;
    const instruction = text.trim();
    ws.setWorkspacePickError(null);
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
        ws.setWorkspacePickError(message);
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
    ws.setWorkspacePickError(
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


const activeSession = sessions.find(s => s.run_id === sessionRunId);
const sessionTitle = activeSession ? (activeSession.title || activeSession.workflow_id || activeSession.run_id) : '';


  return {
    appVersion,
    sessionRunId,
    highlightedDispatchEntryId,
    setHighlightedDispatchEntryId,
    highlightedLogIndex,
    setHighlightedLogIndex,
    clutchStatus,
    isTurnInProgress,
    chatMessages,
    terminalLogs,
    appMode,
    setAppMode,
    currentFlowName,
    setCurrentFlowName,
    selectedWorkflowId,
    workflowAgentSteps,
    isMultiAgent,
    sidebarOpen,
    setSidebarOpen,
    rightPanelOpen,
    setRightPanelOpen,
    folders,
    setFolders,
    sessions,
    loadingSessionId,
    historySessionViewRunId,
    shellSnapshotRunIds,
    highRiskConfirmed,
    branchMenuOpen,
    agentMenuOpen,
    workflowMenuOpen,
    footerWorkflows,
    closeFooterMenus,
    selectedAgentId,
    workspaceViewMode,
    configuredAgents,
    inputValue,
    setInputValue,
    rightTab,
    setRightTab,
    uncommitted,
    setUncommitted,
    slashNotice,
    chatSkills,
    selectedSidebarWidth,
    rightSidebarWidth,
    effectiveWorkflowId,
    effectiveWorkflowName,
    selectedAgentName,
    isPlainLlmFooter,
    hideFooterSessionControls,
    footerSelectableAgents,
    mentionableAgents,
    activeWorkflowLabel,
    hasWorkflowSelection,
    multiAgentFooterName,
    showFooterModel,
    agentBoundModelId,
    footerEffectiveModelId,
    footerEffectiveModelName,
    isWorkflowChat,
    chatActiveAgentName,
    chatActiveAgentAvatar,
    customAgentEngineLabel,
    chatRuntimeEngineHint,
    chatLlmModelName,
    resolveAgentLogo,
    selectedAgent,
    hasCliAgents,
    sessionTitle,
    handleSetIsMultiAgent,
    handleActivateAgent,
    handleWorkspaceViewModeChange,
    handleViewToolStepInTerminal,
    syncSelectedAgentFromMention,
    handleClearTerminal,
    handleStopRun,
    handleContinueRun,
    handleApprove,
    handleReject,
    handleRetryWithInstructions,
    handleAnswerQuestion,
    dismissSlashNotice,
    handleSlashCommand,
    bindWorkflowForChat,
    handleFlowSelect,
    handleUseWorkflowInChat,
    toggleWorkflowMenu,
    toggleAgentMenu,
    handleFooterAgentSelect,
    handleNewChat,
    handleNewDesign,
    handleDesignBusyChange,
    handleAppModeChange,
    handleSelectSession,
    handleNewChatInWorkspace,
    handleDeleteSession,
    handleSendMessage,
    handleClearSessionView,
    clearWorkflowSelection,
    selectDefaultAgent,
    promptLeaveTerminal,
    refreshSessions,
    permissionMode: settings.permissionMode,
    handlePermissionModeChange,
  };
}
