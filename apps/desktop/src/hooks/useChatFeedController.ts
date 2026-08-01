import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import {
  APP_INPUT_DOCK_BOTTOM_PX,
  CHAT_SCROLL_ABOVE_DOCK_GAP_PX,
} from '../constants/layout';
import {
  AgentGoal,
  BackgroundJob,
  ChatMessage,
  ClutchRunStatus,
  HybridExecutionPayload,
  QuestionOption,
  SubtaskCard,
  TodoItem,
  ToolStep,
} from '../types';
import { useLanguage } from '../components/LanguageContext';
import type { Attachment } from '../components/ChatInputBar';
import {
  dequeueOnIdle,
  enqueuePendingMessage,
  removePendingMessage,
  shouldEnqueueAgentMessage,
  type PendingChatMessage,
} from '../services/chatPendingQueue';
import { forkSession, rewindFileWrites, type SessionRecord } from '../services/runApi';
import type { ScannedSkill } from '../services/skillsApi';
import type { FileTreeNode } from '../services/workspaceApi';
import type { PermissionMode } from '../services/permissionApi';
import { clutchStore, useClutchState } from '../services/clutchState';
import {
  pickPrimaryHtmlPath,
  resolveLiveActivitySteps,
  wantsBrowserPreview,
} from '../services/agentActivitySteps';
import { formatPlanRevisePayload, hasPlanStepComments } from '../components/PlanCardView';
import { shouldPinLiveTodos } from '../components/TodoCardView';
import { shouldShowGoalBar } from '../components/GoalBarView';
import { detectBgJobFailureToast } from '../services/bgJobMonitor';
import { resolveBrandLogoSrc } from '../services/brandLogos';
import {
  buildWorkflowReplyStepIndex,
  isWorkflowRefineEligible,
  resolveInProgressWorkflowStep,
} from '../services/workflowAgentSteps';
import { chatChromeForHost } from '../platform/chrome/chatChrome';
import { useHostOs } from '../platform/hostOs';
import { renderChatMarkdown } from '../components/chatContentRender';
import {
  parseInputAgentMention,
  sessionHasTerminalHistory,
  isArchivedTerminalHistoryView,
  shouldConfirmLeavingTerminal,
} from '../services/terminalOrchestraUtils';
import {
  buildTerminalLayoutChromeKey,
  TERMINAL_COLLAPSED_TOGGLE_GUTTER_PX,
} from '../components/terminal-orchestra/terminalLaneLayout';
import {
  resolveCliToolForTerminal,
  saveWorkspaceViewMode,
  type WorkspaceViewMode,
} from '../services/workspaceViewMode';

function isPlainLlmSession(
  selectedWorkflowId: string | null | undefined,
  activeWorkflowId: string | undefined,
): boolean {
  return !selectedWorkflowId && !activeWorkflowId;
}

/** Map agent-configured engine label to runtime label from the sidecar. */
export function configuredEngineToRuntimeLabel(agentTypeOrLegacy: string): string {
  const key = agentTypeOrLegacy.trim().toLowerCase();
  if (key === 'clutch' || key.includes('configured llm')) return 'Clutch';
  if (key.includes('claude') || key === 'claude-cli') return 'Claude CLI';
  if (key.includes('antigravity') || key.includes('agenty') || key === 'agy-cli' || key === 'antigravity-cli') {
    return 'Antigravity CLI';
  }
  if (key.includes('codex') || key === 'codex-cli') return 'Codex CLI';
  if (key.includes('ollama') || key === 'ollama-cli') return 'Ollama CLI';
  if (key.includes('zcode') || key === 'zcode-cli') return 'ZCode CLI';
  return agentTypeOrLegacy.trim();
}

export interface UseChatFeedControllerParams {
  messages: ChatMessage[];
  hybridExecutions?: Record<string, HybridExecutionPayload>;
  inputValue: string;
  setInputValue: (val: string) => void;
  onSendMessage: (text: string, attachments?: Attachment[]) => void;
  clutchStatus: ClutchRunStatus;
  currentFlowName?: string;
  selectedSidebarWidth: number;
  rightSidebarWidth: number;
  sidebarOpen?: boolean;
  rightPanelOpen?: boolean;
  onStopRun?: () => boolean | void;
  onContinueRun?: () => void;
  isMultiAgent?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onRetryWithInstructions?: (instructions: string) => void;
  onAnswerQuestion?: (option: QuestionOption) => void;
  workspaceAuthorized?: boolean;
  onPickWorkspace?: () => void;
  onOpenWorkflows?: () => void;
  workspacePickError?: string | null;
  selectedWorkflowId?: string | null;
  selectedWorkflowName?: string;
  onClearSelectedWorkflow?: () => void;
  sessionTitle?: string;
  sessionRunId?: string;
  activeWorkflowId?: string;
  llmModelName?: string;
  activeAgentName?: string;
  activeAgentAvatar?: string;
  activeNodeId?: string;
  workflowAgentSteps?: Array<{ nodeId: string; agentName: string; agentType: string; toolId?: string; agentRef?: string; label?: string }>;
  resolveAgentLogo?: (agentName: string) => string | undefined;
  engineHint?: string;
  activeAgentType?: string;
  workspaceViewMode: WorkspaceViewMode;
  onWorkspaceViewModeChange: (mode: WorkspaceViewMode) => void;
  onLeaveTerminalConfirm?: (onProceed: () => void) => void;
  highlightedDispatchEntryId?: string | null;
  hasCliAgents?: boolean;
  workspaceFiles?: FileTreeNode[];
  sessions?: SessionRecord[];
  skills?: ScannedSkill[];
  permissionMode?: PermissionMode;
  onPermissionModeChange?: (mode: PermissionMode) => void;
  shellSessionStatus?: string;
  shellPoolBlockerRunIds?: string[];
  shellPoolBlockers?: Array<{ run_id: string; title?: string; agent_name?: string }>;
  shellPoolQueuePosition?: number;
  shellPoolQueueDepth?: number;
  userAvatar?: string;
  userName?: string;
  terminalLogs?: string[];
  onClearTerminal?: () => void;
  mentionableAgents?: Array<{ id: string; name: string; logo?: string; dispatchTarget: string; agentType?: string }>;
  selectedMentionAgentId?: string | null;
  onMentionAgentChange?: (agentId: string | null) => void;
  workspacePath?: string;
  isHistorySessionView?: boolean;
  onOpenWorkspaceFile?: (path: string) => void;
  onPreviewSnippet?: (name: string, content: string) => void;
  onViewToolStepInTerminal?: (step: ToolStep) => void;
  onSelectSession?: (session: SessionRecord) => void;
  mcpServerIds?: string[];
  showMcpBindingBadge?: boolean;
  onOpenMcpBind?: () => void;
  onSlashCommand?: (id: import('../services/slashCommands').SlashCommandId) => void | Promise<void>;
  slashNotice?: string | null;
  onDismissSlashNotice?: () => void;
}

export function useChatFeedController(params: UseChatFeedControllerParams) {
  const {
    messages,
    hybridExecutions,
    inputValue,
    onSendMessage,
    clutchStatus,
    currentFlowName = '',
    selectedSidebarWidth,
    rightSidebarWidth,
    sidebarOpen = true,
    rightPanelOpen = true,
    onStopRun,
    onApprove,
    onReject,
    onRetryWithInstructions,
    onAnswerQuestion,
    workspacePickError = null,
    selectedWorkflowId = null,
    selectedWorkflowName = '',
    onClearSelectedWorkflow,
    sessionTitle = '',
    sessionRunId = '',
    activeWorkflowId = '',
    llmModelName = '',
    activeAgentName = '',
    activeAgentAvatar,
    activeNodeId = '',
    workflowAgentSteps = [],
    resolveAgentLogo,
    engineHint = '',
    workspaceViewMode,
    onWorkspaceViewModeChange,
    onLeaveTerminalConfirm,
    highlightedDispatchEntryId = null,
    hasCliAgents = false,
    workspaceFiles = [],
    sessions = [],
    skills = [],
    permissionMode = 'auto_edit',
    onPermissionModeChange,
    shellSessionStatus,
    shellPoolBlockerRunIds = [],
    shellPoolBlockers = [],
    shellPoolQueuePosition = 0,
    shellPoolQueueDepth = 0,
    userAvatar,
    userName = 'User',
    mentionableAgents = [],
    selectedMentionAgentId = null,
    onMentionAgentChange,
    workspacePath,
    isHistorySessionView = false,
    onOpenWorkspaceFile,
    onPreviewSnippet,
    onViewToolStepInTerminal,
    onSelectSession,
    mcpServerIds,
    showMcpBindingBadge = false,
    onOpenMcpBind,
    onSlashCommand,
    slashNotice = null,
    onDismissSlashNotice,
    isMultiAgent = true,
    workspaceAuthorized = false,
    onPickWorkspace,
    onOpenWorkflows,
    onContinueRun,
    setInputValue,
  } = params;

  const { t, language } = useLanguage();
  const hostOs = useHostOs();
  const chatChrome = chatChromeForHost(hostOs, sidebarOpen, rightPanelOpen);
  const markdownHandlers = useMemo(
    () => ({
      onOpenPath: onOpenWorkspaceFile,
      onPreviewSnippet,
    }),
    [onOpenWorkspaceFile, onPreviewSnippet],
  );
  const renderMarkdown = useCallback(
    (text: string) => renderChatMarkdown(text, markdownHandlers),
    [markdownHandlers],
  );
  const { state: clutchOrchestraState } = useClutchState();
  const [orchestratorBarFocused, setOrchestratorBarFocused] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const thinkingRef = useRef<HTMLDivElement>(null);
  const dockRef = useRef<HTMLDivElement>(null);
  const terminalDockRef = useRef<HTMLDivElement>(null);
  const terminalBarRef = useRef<HTMLDivElement>(null);
  const terminalStageRef = useRef<HTMLDivElement>(null);
  const [dockClearance, setDockClearance] = useState(
    APP_INPUT_DOCK_BOTTOM_PX + 120 + CHAT_SCROLL_ABOVE_DOCK_GAP_PX,
  );
  const [thinkingHeight, setThinkingHeight] = useState(0);
  const [terminalBarHeight, setTerminalBarHeight] = useState(52);
  const [hillInstructions, setHillInstructions] = useState('');
  const [planStepComments, setPlanStepComments] = useState<string[]>([]);
  const [pendingMessages, setPendingMessages] = useState<PendingChatMessage[]>([]);
  const [bgJobToast, setBgJobToast] = useState<string | null>(null);
  const prevBgJobsRef = useRef<BackgroundJob[]>([]);
  const autoOpenedHtmlRef = useRef<Set<string>>(new Set());
  const wasRunningForHtmlRef = useRef(false);
  const htmlAutoOpenArmedRef = useRef(false);
  const [messageContextMenu, setMessageContextMenu] = useState<{
    x: number;
    y: number;
    messageId: string;
    messageIndex: number;
  } | null>(null);

  useEffect(() => {
    const handleClose = () => setMessageContextMenu(null);
    window.addEventListener('click', handleClose);
    window.addEventListener('contextmenu', handleClose);
    return () => {
      window.removeEventListener('click', handleClose);
      window.removeEventListener('contextmenu', handleClose);
    };
  }, []);

  useEffect(() => {
    setPendingMessages([]);
    autoOpenedHtmlRef.current.clear();
    wasRunningForHtmlRef.current = false;
    htmlAutoOpenArmedRef.current = false;
  }, [sessionRunId]);

  const isIdle = clutchStatus === 'idle';
  const isRefining = isWorkflowRefineEligible(clutchStatus, activeWorkflowId);
  const isRunning = clutchStatus === 'running';
  const awaitingHuman = clutchStatus === 'awaiting_human';
  const [hitlBusy, setHitlBusy] = useState(false);
  const pendingPlanMessage = useMemo(() => {
    if (!awaitingHuman) return null;
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const card = messages[i]?.planCard;
      if (card && card.status === 'pending') return messages[i];
    }
    return null;
  }, [awaitingHuman, messages]);
  const pendingQuestionMessage = useMemo(() => {
    if (!awaitingHuman) return null;
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const card = messages[i]?.questionCard;
      if (card && card.status === 'pending') return messages[i];
    }
    return null;
  }, [awaitingHuman, messages]);
  const awaitingPlan = Boolean(pendingPlanMessage);
  const awaitingQuestion = Boolean(pendingQuestionMessage);

  useEffect(() => {
    const steps = pendingPlanMessage?.planCard?.steps ?? [];
    setPlanStepComments(steps.map(() => ''));
  }, [pendingPlanMessage]);

  const canSubmitPlanRevise =
    hillInstructions.trim().length > 0 || hasPlanStepComments(planStepComments);

  const submitPlanRevise = () => {
    if (!canSubmitPlanRevise || hitlBusy) return;
    setHitlBusy(true);
    const payload = formatPlanRevisePayload(
      hillInstructions,
      pendingPlanMessage?.planCard?.steps ?? [],
      planStepComments,
    );
    onRetryWithInstructions?.(payload);
    setHillInstructions('');
    setPlanStepComments((pendingPlanMessage?.planCard?.steps ?? []).map(() => ''));
  };

  useEffect(() => {
    if (!awaitingHuman) {
      setHitlBusy(false);
    }
  }, [awaitingHuman]);

  const isPlainLlmChat = isPlainLlmSession(selectedWorkflowId, activeWorkflowId);
  const sessionDispatched = sessionHasTerminalHistory(clutchOrchestraState);
  const isTerminalDispatchHistoryReadonly = isPlainLlmChat && hasCliAgents
    && isArchivedTerminalHistoryView(clutchOrchestraState, workspaceViewMode);
  const showWorkspaceReadonlyChrome = isPlainLlmChat && hasCliAgents
    && (isHistorySessionView || isTerminalDispatchHistoryReadonly);
  const hasPersistedTerminalLanes = (clutchOrchestraState.pty_lanes ?? []).some(
    (lane) => lane.status !== 'queued',
  );
  const inputTerminalMention = useMemo(
    () => parseInputAgentMention(inputValue, mentionableAgents),
    [inputValue, mentionableAgents],
  );
  const inputPreviewAgentType = useMemo(() => {
    if (!inputTerminalMention) return null;
    const match = mentionableAgents.find((agent) => agent.id === inputTerminalMention.agentId);
    const agentType = match?.agentType?.trim();
    if (!agentType) return null;
    return resolveCliToolForTerminal(agentType);
  }, [inputTerminalMention, mentionableAgents]);
  const showWorkspaceViewToggle = isPlainLlmChat && hasCliAgents && !showWorkspaceReadonlyChrome;
  const showTerminalWorkspace = workspaceViewMode === 'terminal' && isPlainLlmChat && hasCliAgents;
  const hasTerminalSession = (sessionDispatched && hasPersistedTerminalLanes) || Boolean(inputPreviewAgentType);
  const keepTerminalMounted = isPlainLlmChat && hasCliAgents && hasTerminalSession;
  const isTerminalLayout = showTerminalWorkspace;
  const terminalInputReservePx = terminalBarHeight + APP_INPUT_DOCK_BOTTOM_PX;
  const terminalDockHeight = terminalBarHeight * 2 + APP_INPUT_DOCK_BOTTOM_PX;

  const leftChromePad =
    selectedSidebarWidth + chatChrome.sidebarContentInset + (sidebarOpen ? 0 : TERMINAL_COLLAPSED_TOGGLE_GUTTER_PX);
  const rightChromePad =
    rightSidebarWidth + chatChrome.rightContentInset + (rightPanelOpen ? 0 : TERMINAL_COLLAPSED_TOGGLE_GUTTER_PX);

  const terminalLayoutChromeKey = buildTerminalLayoutChromeKey({
    sidebarWidth: selectedSidebarWidth,
    rightPanelWidth: rightSidebarWidth,
    dockHeight: showTerminalWorkspace ? terminalDockHeight : dockClearance,
    sidebarOpen,
    rightPanelOpen,
    workspaceViewMode,
  });
  const terminalPreviewAgentType = sessionDispatched ? null : inputPreviewAgentType;

  useEffect(() => {
    if (hasTerminalSession || sessionDispatched) return;
    void clutchStore.detachInteractivePty('lane_primary');
  }, [hasTerminalSession, sessionDispatched]);

  useEffect(() => {
    if (!isTerminalDispatchHistoryReadonly || workspaceViewMode === 'chat') return;
    onWorkspaceViewModeChange('chat');
    saveWorkspaceViewMode('chat');
    void clutchStore.detachInteractivePty();
  }, [isTerminalDispatchHistoryReadonly, workspaceViewMode, onWorkspaceViewModeChange]);

  useEffect(() => {
    if (!showWorkspaceViewToggle && workspaceViewMode === 'terminal') {
      onWorkspaceViewModeChange('chat');
      saveWorkspaceViewMode('chat');
      void clutchStore.detachInteractivePty();
    }
  }, [showWorkspaceViewToggle, workspaceViewMode, onWorkspaceViewModeChange]);

  const handleWorkspaceViewChange = useCallback((mode: WorkspaceViewMode) => {
    if (
      mode === 'chat'
      && shouldConfirmLeavingTerminal(
        clutchOrchestraState,
        workspaceViewMode,
        inputValue,
        mentionableAgents,
      )
      && onLeaveTerminalConfirm
    ) {
      onLeaveTerminalConfirm(() => {
        onWorkspaceViewModeChange('chat');
        saveWorkspaceViewMode('chat');
      });
      return;
    }
    onWorkspaceViewModeChange(mode);
    saveWorkspaceViewMode(mode);
  }, [
    clutchOrchestraState,
    workspaceViewMode,
    inputValue,
    mentionableAgents,
    onLeaveTerminalConfirm,
    onWorkspaceViewModeChange,
  ]);

  const prevStatusRef = useRef(clutchStatus);
  useEffect(() => {
    const prevStatus = prevStatusRef.current;
    prevStatusRef.current = clutchStatus;
    if (!isPlainLlmChat) return;
    const { next, rest } = dequeueOnIdle(prevStatus, clutchStatus, pendingMessages);
    if (!next) return;
    setPendingMessages(rest);
    onSendMessage(next.text);
  }, [clutchStatus, isPlainLlmChat, pendingMessages, onSendMessage]);

  const enqueuePending = useCallback((text: string) => {
    setPendingMessages((prev) => enqueuePendingMessage(text, prev));
  }, []);

  const removePending = useCallback((id: string) => {
    setPendingMessages((prev) => removePendingMessage(id, prev));
  }, []);

  const handleMessageContextMenu = useCallback(
    (e: React.MouseEvent, messageId: string, messageIndex: number) => {
      e.preventDefault();
      e.stopPropagation();
      setMessageContextMenu({
        x: e.clientX,
        y: e.clientY,
        messageId,
        messageIndex,
      });
    },
    [],
  );

  const handleForkSession = useCallback(
    async (messageIndex: number) => {
      if (!sessionRunId || !isPlainLlmChat) return;
      try {
        const result = await forkSession(sessionRunId, messageIndex);
        const session: SessionRecord = {
          run_id: result.run_id,
          title: result.title,
          workflow_id: '',
          status: 'idle',
          started_at: new Date().toISOString(),
          parent_run_id: result.parent_run_id,
          fork_message_index: result.message_index,
        };
        onSelectSession?.(session);
      } catch (error) {
        console.error('[Clutch] fork session failed:', error);
      }
    },
    [sessionRunId, isPlainLlmChat, onSelectSession],
  );

  const handleRewindFiles = useCallback(async () => {
    if (!sessionRunId || !isPlainLlmChat) return;
    try {
      const result = await rewindFileWrites(sessionRunId, 1);
      if (result.state) {
        clutchStore.replaceState(result.state);
      }
    } catch (error) {
      console.error('[Clutch] rewind files failed:', error);
    }
  }, [sessionRunId, isPlainLlmChat]);

  const handleStopWithQueueClear = useCallback((): boolean => {
    const proceeded = onStopRun?.();
    if (proceeded === false) return false;
    setPendingMessages([]);
    return true;
  }, [onStopRun]);

  const handleSendWithAttachments = (text: string, attachments: Attachment[]) => {
    let fullText = text;
    for (const att of attachments) {
      if (att.kind === 'image' && att.dataUrl) {
        fullText = `[image: ${att.dataUrl}]\n${fullText}`;
      } else if (att.path) {
        fullText = `[file: ${att.path}]\n${fullText}`;
      } else {
        fullText = `[file: ${att.name}]\n${fullText}`;
      }
    }
    const trimmed = fullText.trim();
    if (!trimmed) return;
    if (shouldEnqueueAgentMessage(isRunning, isPlainLlmChat)) {
      enqueuePending(trimmed);
      return;
    }
    onSendMessage(trimmed, attachments);
  };

  const isDefaultNewSessionTitle = !sessionTitle ||
    sessionTitle === 'New session' ||
    sessionTitle === 'New Chat' ||
    sessionTitle === 'New session / 新建会话' ||
    sessionTitle === 'New Chat / 新建会话' ||
    sessionTitle === '新建会话';

  const showEmptyState = isIdle && messages.length === 0 && isDefaultNewSessionTitle && !showWorkspaceReadonlyChrome;

  const workflowReplyStepIndex = useMemo(
    () => buildWorkflowReplyStepIndex(workflowAgentSteps, messages),
    [workflowAgentSteps, messages],
  );

  const lastUserIndex = messages.findLastIndex((message) => message.agent === 'User');
  const lastAgentIndex = messages.findLastIndex((message) => message.agent !== 'User');
  const inProgressWorkflowStep =
    isRunning && !isPlainLlmChat
      ? (
        resolveInProgressWorkflowStep(workflowAgentSteps, messages, {
          activeNodeId,
          activeAgentName,
        })
        ?? (
          workflowAgentSteps.length === 0 && lastUserIndex >= 0 && lastUserIndex > lastAgentIndex
            ? {
                nodeId: activeNodeId || '',
                agentName: activeAgentName,
                agentType: engineHint || '',
                toolId: '',
              }
            : null
        )
      )
      : null;
  const thinkingAgentName = isPlainLlmChat
    ? activeAgentName
    : (inProgressWorkflowStep?.agentName || activeAgentName);
  const thinkingAgentType = isPlainLlmChat
    ? (engineHint || '')
    : (inProgressWorkflowStep?.agentType || '');
  const thinkingAgentLogo =
    resolveBrandLogoSrc({ toolId: inProgressWorkflowStep?.toolId })
    ?? resolveAgentLogo?.(thinkingAgentName);
  const showWorkflowThinking = Boolean(inProgressWorkflowStep);
  const showThinking =
    (isRunning && isPlainLlmChat) || showWorkflowThinking;

  const pendingToolSteps = clutchOrchestraState.pending_tool_steps;
  const liveTodos = (clutchOrchestraState.agent_todos ?? []) as TodoItem[];
  const liveGoal = clutchOrchestraState.agent_goal as AgentGoal | undefined;
  const showGoalBar = shouldShowGoalBar(liveGoal);
  const liveSubtasks = (clutchOrchestraState.pending_subtasks ?? []) as SubtaskCard[];
  const bgJobs = (clutchOrchestraState.bg_jobs ?? []) as BackgroundJob[];
  const sealedBgJobIds = useMemo(() => {
    const ids = new Set<string>();
    for (const msg of messages) {
      if (msg.bgJob?.id) ids.add(msg.bgJob.id);
    }
    return ids;
  }, [messages]);
  const feedFallbackBgJobs = useMemo(
    () =>
      bgJobs.filter(
        (job) => job.status !== 'running' && !sealedBgJobIds.has(job.id),
      ),
    [bgJobs, sealedBgJobIds],
  );
  const foregroundShell = clutchOrchestraState.foreground_shell ?? null;
  const worktreeIsolation = clutchOrchestraState.worktree_isolation ?? null;
  const chatDiagnostics = clutchOrchestraState.chat_diagnostics ?? [];

  useEffect(() => {
    const prev = prevBgJobsRef.current;
    prevBgJobsRef.current = bgJobs;
    const failedTitle = detectBgJobFailureToast(prev, bgJobs);
    if (!failedTitle) return;
    setBgJobToast(
      language === 'zh'
        ? `后台任务失败：${failedTitle}`
        : `Background job failed: ${failedTitle}`,
    );
  }, [bgJobs, language]);

  useEffect(() => {
    if (!bgJobToast) return undefined;
    const timer = window.setTimeout(() => setBgJobToast(null), 4000);
    return () => window.clearTimeout(timer);
  }, [bgJobToast]);

  const pinLiveTodos = shouldPinLiveTodos(liveTodos, { isRunning, awaitingHuman });
  const showInlineLiveTodos = liveTodos.length > 0 && !pinLiveTodos;
  const liveActivitySteps = useMemo(
    () =>
      resolveLiveActivitySteps(pendingToolSteps, clutchOrchestraState.terminal_logs, {
        awaiting: awaitingHuman,
      }),
    [pendingToolSteps, clutchOrchestraState.terminal_logs, awaitingHuman],
  );
  const liveReasoning = clutchOrchestraState.live_reasoning?.trim() || '';
  const showLiveActivity =
    (liveActivitySteps.length > 0 || liveReasoning.length > 0) &&
    (showThinking || awaitingHuman || (isRunning && isPlainLlmChat));

  const lastUserPromptForHtml = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i]?.agent === 'User') return messages[i]?.text ?? '';
    }
    return '';
  }, [messages]);
  const shouldAutoOpenHtml = wantsBrowserPreview(lastUserPromptForHtml);

  useEffect(() => {
    if (!onOpenWorkspaceFile || !isRunning) return;

    const completedHtml: string[] = [];
    for (const step of liveActivitySteps) {
      if (step.status !== 'completed') continue;
      const path = step.fileDiff?.path?.trim();
      if (path) completedHtml.push(path);
    }

    if (!htmlAutoOpenArmedRef.current) {
      htmlAutoOpenArmedRef.current = true;
      for (const path of completedHtml) {
        const primary = pickPrimaryHtmlPath([path]);
        if (primary) autoOpenedHtmlRef.current.add(`${sessionRunId}:${primary}`);
      }
      return;
    }

    if (!shouldAutoOpenHtml) return;
    const primary = pickPrimaryHtmlPath(completedHtml);
    if (!primary) return;
    const key = `${sessionRunId}:${primary}`;
    if (autoOpenedHtmlRef.current.has(key)) return;
    autoOpenedHtmlRef.current.add(key);
    onOpenWorkspaceFile(primary);
  }, [
    liveActivitySteps,
    onOpenWorkspaceFile,
    sessionRunId,
    isRunning,
    shouldAutoOpenHtml,
  ]);

  useEffect(() => {
    const justFinished = wasRunningForHtmlRef.current && !isRunning;
    wasRunningForHtmlRef.current = isRunning;
    if (
      !justFinished ||
      !htmlAutoOpenArmedRef.current ||
      !onOpenWorkspaceFile ||
      !shouldAutoOpenHtml
    ) {
      return;
    }
    const last = messages[messages.length - 1];
    if (!last || last.agent === 'User' || !last.filesChanged?.length) return;
    const primary = pickPrimaryHtmlPath(last.filesChanged);
    if (!primary) return;
    const key = `${sessionRunId}:${primary}`;
    if (autoOpenedHtmlRef.current.has(key)) return;
    autoOpenedHtmlRef.current.add(key);
    onOpenWorkspaceFile(primary);
  }, [isRunning, messages, onOpenWorkspaceFile, sessionRunId, shouldAutoOpenHtml]);

  const chatScrollBottomPad = useMemo(
    () =>
      dockClearance +
      (showThinking ? thinkingHeight + 16 : 0) +
      (awaitingHuman && showLiveActivity && !showThinking ? 12 : 0),
    [dockClearance, showThinking, thinkingHeight, awaitingHuman, showLiveActivity],
  );

  const scrollChatToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    bottomRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, []);

  const scrollChatAboveDock = useCallback((behavior: ScrollBehavior = 'auto') => {
    const run = () => scrollChatToBottom(behavior);
    requestAnimationFrame(() => {
      requestAnimationFrame(run);
    });
  }, [scrollChatToBottom]);

  useEffect(() => {
    scrollChatToBottom();
  }, [messages, clutchStatus, showThinking, pendingMessages.length, scrollChatToBottom]);

  useEffect(() => {
    scrollChatAboveDock('auto');
  }, [dockClearance, scrollChatAboveDock]);

  const bgJobsChromeKey = `${bgJobs.length}:${bgJobs.map((job) => job.status).join(',')}`;

  useEffect(() => {
    const dock = dockRef.current;
    if (!dock || showTerminalWorkspace) return;
    const measure = () => {
      const next =
        APP_INPUT_DOCK_BOTTOM_PX + dock.offsetHeight + CHAT_SCROLL_ABOVE_DOCK_GAP_PX;
      setDockClearance((prev) => (prev === next ? prev : next));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(dock);
    return () => observer.disconnect();
  }, [
    pendingMessages.length,
    shellSessionStatus,
    awaitingHuman,
    awaitingPlan,
    awaitingQuestion,
    isRunning,
    isPlainLlmChat,
    showTerminalWorkspace,
    llmModelName,
    showLiveActivity,
    liveActivitySteps.length,
    bgJobsChromeKey,
    foregroundShell?.command,
    chatDiagnostics.length,
    worktreeIsolation?.enabled,
  ]);

  useEffect(() => {
    if (showTerminalWorkspace) return;
    const dock = dockRef.current;
    if (!dock) return;
    const id = window.requestAnimationFrame(() => {
      const next =
        APP_INPUT_DOCK_BOTTOM_PX + dock.offsetHeight + CHAT_SCROLL_ABOVE_DOCK_GAP_PX;
      setDockClearance((prev) => (prev === next ? prev : next));
      scrollChatAboveDock('auto');
    });
    return () => window.cancelAnimationFrame(id);
  }, [bgJobsChromeKey, showTerminalWorkspace, scrollChatAboveDock]);

  useEffect(() => {
    const thinkingEl = thinkingRef.current;
    if (!thinkingEl || !showThinking) {
      setThinkingHeight(0);
      return;
    }
    const measure = () => setThinkingHeight(thinkingEl.offsetHeight);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(thinkingEl);
    return () => observer.disconnect();
  }, [showThinking, llmModelName, thinkingAgentName, thinkingAgentType, liveActivitySteps.length]);

  useEffect(() => {
    if (!showLiveActivity) return;
    scrollChatToBottom();
  }, [liveActivitySteps.length, showLiveActivity, scrollChatToBottom]);

  useEffect(() => {
    const terminalBar = terminalBarRef.current;
    if (!terminalBar || !showTerminalWorkspace) return;
    const measure = () => {
      setTerminalBarHeight(terminalBar.offsetHeight);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(terminalBar);
    return () => observer.disconnect();
  }, [showTerminalWorkspace, inputValue, clutchOrchestraState.pending_handoff_drafts?.length]);

  const workspaceChromeRowClass = (extra = '') =>
    `flex justify-end shrink-0 ${isTerminalLayout ? 'mb-3' : 'mb-6'} ${extra}`.trim();

  return {
    t,
    chatChrome,
    renderMarkdown,
    clutchOrchestraState,
    orchestratorBarFocused,
    setOrchestratorBarFocused,
    bottomRef,
    thinkingRef,
    dockRef,
    terminalDockRef,
    terminalBarRef,
    terminalStageRef,
    hillInstructions,
    setHillInstructions,
    planStepComments,
    setPlanStepComments,
    pendingMessages,
    bgJobToast,
    messageContextMenu,
    setMessageContextMenu,
    hitlBusy,
    setHitlBusy,
    isIdle,
    isRefining,
    isRunning,
    awaitingHuman,
    pendingPlanMessage,
    pendingQuestionMessage,
    awaitingPlan,
    awaitingQuestion,
    canSubmitPlanRevise,
    submitPlanRevise,
    isPlainLlmChat,
    sessionDispatched,
    isTerminalDispatchHistoryReadonly,
    showWorkspaceReadonlyChrome,
    showWorkspaceViewToggle,
    showTerminalWorkspace,
    keepTerminalMounted,
    isTerminalLayout,
    terminalInputReservePx,
    terminalBarHeight,
    leftChromePad,
    rightChromePad,
    terminalLayoutChromeKey,
    terminalPreviewAgentType,
    inputTerminalMention,
    handleWorkspaceViewChange,
    removePending,
    handleMessageContextMenu,
    handleForkSession,
    handleRewindFiles,
    handleStopWithQueueClear,
    handleSendWithAttachments,
    showEmptyState,
    workflowReplyStepIndex,
    thinkingAgentName,
    thinkingAgentType,
    thinkingAgentLogo,
    activeAgentAvatar,
    showThinking,
    liveTodos,
    liveGoal,
    showGoalBar,
    liveSubtasks,
    bgJobs,
    feedFallbackBgJobs,
    foregroundShell,
    worktreeIsolation,
    chatDiagnostics,
    pinLiveTodos,
    showInlineLiveTodos,
    liveActivitySteps,
    liveReasoning,
    showLiveActivity,
    chatScrollBottomPad,
    workspaceChromeRowClass,
    llmModelName,
    engineHint,
    workflowAgentSteps,
    resolveAgentLogo,
    userAvatar,
    userName,
    hybridExecutions,
    onOpenWorkspaceFile,
    onViewToolStepInTerminal,
    onAnswerQuestion,
    onApprove,
    onReject,
    onRetryWithInstructions,
    onContinueRun,
    inputValue,
    setInputValue,
    permissionMode,
    onPermissionModeChange,
    workspaceFiles,
    sessions,
    skills,
    mentionableAgents,
    selectedMentionAgentId,
    onMentionAgentChange,
    sessionRunId,
    clutchStatus,
    selectedWorkflowId,
    selectedWorkflowName,
    onClearSelectedWorkflow,
    isMultiAgent,
    workspaceAuthorized,
    onPickWorkspace,
    onOpenWorkflows,
    workspacePickError,
    shellSessionStatus,
    shellPoolBlockerRunIds,
    shellPoolBlockers,
    shellPoolQueuePosition,
    shellPoolQueueDepth,
    onSelectSession,
    mcpServerIds,
    showMcpBindingBadge,
    onOpenMcpBind,
    onSlashCommand,
    slashNotice,
    onDismissSlashNotice,
    onStopRun,
    currentFlowName,
    workspaceViewMode,
    highlightedDispatchEntryId,
    workspacePath,
    activeAgentName,
    hasCliAgents,
  };
}
