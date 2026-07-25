import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import {
  APP_FOOTER_HEIGHT_PX,
  APP_HEADER_HEIGHT_PX,
  APP_INPUT_DOCK_BOTTOM_PX,
  CHAT_SCROLL_ABOVE_DOCK_GAP_PX,
  WORKSPACE_CHROME_ROW_TOP_PX,
} from '../constants/layout';
import { ChevronRight } from 'lucide-react';
import {
  ChatMessage,
  ClutchRunStatus,
  HybridExecutionPayload,
  OutputEvent,
  QuestionOption,
  SubtaskCard,
  TodoItem,
  AgentGoal,
  BackgroundJob,
  ToolStep,
} from '../types';
import { useLanguage } from './LanguageContext';
import { ChatInputBar, type Attachment } from './ChatInputBar';
import {
  dequeueOnIdle,
  enqueuePendingMessage,
  removePendingMessage,
  shouldEnqueueAgentMessage,
  type PendingChatMessage,
} from '../services/chatPendingQueue';
import { BTN_PRIMARY, BTN_SECONDARY, BTN_SM } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { forkSession, rewindFileWrites, type SessionRecord } from '../services/runApi';
import type { ScannedSkill } from '../services/skillsApi';
import type { FileTreeNode } from '../services/workspaceApi';
import type { PermissionMode } from '../services/permissionApi';
import { USER_CHAT_AVATAR, clutchStore, deleteChatMessage, useClutchState } from '../services/clutchState';
import { resolveLiveActivitySteps } from '../services/agentActivitySteps';
import { AgentLiveActivity } from './AgentLiveActivity';
import { FilesChangedChips } from './FilesChangedChips';
import { PlanCardView, formatPlanRevisePayload, hasPlanStepComments } from './PlanCardView';
import { QuestionCardView } from './QuestionCardView';
import { TodoCardView, shouldPinLiveTodos } from './TodoCardView';
import { GoalBarView, shouldShowGoalBar } from './GoalBarView';
import { SubtaskCardView } from './SubtaskCardView';
import { BackgroundJobsBar } from './BackgroundJobsBar';
import { ForegroundShellBar } from './ForegroundShellBar';
import { DiagnosticsIssuesStrip } from './DiagnosticsIssuesStrip';
import { WorktreeIsolationBar } from './WorktreeIsolationBar';
import { detectBgJobFailureToast } from '../services/bgJobMonitor';
import { VerificationReportCardView } from './VerificationReportCardView';
import { DiffSummaryCardView } from './DiffSummaryCardView';
import { resolveBrandLogoSrc } from '../services/brandLogos';
import { clutchMarkUrl } from '../assets/brand';
import { AgentChatAvatar } from './AgentChatAvatar';
import { ChatBubbleVideo } from './ChatBubbleVideo';
import {
  buildWorkflowReplyStepIndex,
  isWorkflowRefineEligible,
  resolveInProgressWorkflowStep,
} from '../services/workflowAgentSteps';
import { OrchestratorBar } from './terminal-orchestra/OrchestratorBar';
import { TerminalOrchestraWorkspace } from './terminal-orchestra/TerminalOrchestraWorkspace';
import { chatChromeForHost } from '../platform/chrome/chatChrome';
import { useHostOs } from '../platform/hostOs';
import { TerminalOrchestraEmptyState } from './terminal-orchestra/TerminalOrchestraEmptyState';
import { TerminalDispatchHistoryFeed } from './terminal-orchestra/TerminalDispatchHistoryFeed';
import { renderChatMarkdown } from './chatContentRender';
import {
  parseInputAgentMention,
  sessionHasTerminalHistory,
  isArchivedTerminalHistoryView,
  shouldConfirmLeavingTerminal,
} from '../services/terminalOrchestraUtils';
import {
  buildTerminalLayoutChromeKey,
  TERMINAL_COLLAPSED_TOGGLE_GUTTER_PX,
  XTERM_KEEPALIVE_STYLE,
} from './terminal-orchestra/terminalLaneLayout';
import {
  resolveCliToolForTerminal,
  saveWorkspaceViewMode,
  type WorkspaceViewMode,
} from '../services/workspaceViewMode';

function outputEventLabel(type: OutputEvent['type'], t: (key: string) => string): string {
  switch (type) {
    case 'shell_echo':
      return t('Shell command');
    case 'system_prompt':
      return t('System prompt');
    case 'boundary_marker':
      return t('Boundary marker');
    default:
      return type;
  }
}

function isHybridReply(msg: ChatMessage): boolean {
  return Boolean(msg.runtimeEngine?.includes('Hybrid'));
}

function resolveAssistantDisplayText(
  msg: ChatMessage,
  hybridExecutions?: Record<string, HybridExecutionPayload>,
): string {
  return resolveAssistantContentSource(msg, hybridExecutions).displayText;
}

/** Hybrid replies show assistant text from outputEvents; images must use the same source. */
function resolveAssistantContentSource(
  msg: ChatMessage,
  hybridExecutions?: Record<string, HybridExecutionPayload>,
): { displayText: string; parseSource: string } {
  const events = hybridExecutions?.[msg.id]?.outputEvents ?? msg.outputEvents;
  const assistantEvent = events?.find(
    (event) => event.type === 'assistant' && event.visible !== false && event.content.trim(),
  );
  if (assistantEvent?.content.trim()) {
    const displayText = assistantEvent.content;
    return { displayText, parseSource: displayText };
  }
  const parsed = parseChatContent(msg.text);
  return { displayText: parsed.text, parseSource: msg.text };
}

function previewExecutionContent(content: string, maxChars = 56): string {
  const singleLine = content.replace(/\s+/g, ' ').trim();
  if (singleLine.length <= maxChars) return singleLine;
  return `${singleLine.slice(0, maxChars)}…`;
}

function DisclosureRow({
  label,
  meta,
  preview,
  open,
  onToggle,
  children,
}: {
  label: string;
  meta?: string;
  preview?: string;
  open: boolean;
  onToggle: () => void;
  children?: React.ReactNode;
}) {
  return (
    <div className="min-w-0">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-1.5 rounded-md py-1 px-1 text-left text-on-surface-variant hover:bg-surface-container/70 hover:text-on-surface transition-colors"
      >
        <ChevronRight
          className={`h-3.5 w-3.5 shrink-0 text-on-surface-variant/60 transition-transform duration-200 ${
            open ? 'rotate-90' : ''
          }`}
          strokeWidth={2}
        />
        <span className="text-[11px] font-medium text-on-surface">{label}</span>
        {meta ? (
          <span className="text-[10px] text-on-surface-variant/55 tabular-nums">{meta}</span>
        ) : null}
      </button>
      {!open && preview ? (
        <p className="ml-[1.35rem] pr-1 text-[10px] font-mono text-on-surface-variant/65 truncate leading-snug">
          {preview}
        </p>
      ) : null}
      {open && children ? (
        <div className="ml-[1.1rem] mt-0.5 mb-1.5 border-l border-outline-variant/25 pl-2.5">
          {children}
        </div>
      ) : null}
    </div>
  );
}

function ExecutionDetailBlock({
  label,
  content,
  tone = 'default',
}: {
  label: string;
  content: string;
  tone?: 'default' | 'muted';
}) {
  const [open, setOpen] = useState(false);
  const preview = previewExecutionContent(content);

  return (
    <DisclosureRow
      label={label}
      preview={preview}
      open={open}
      onToggle={() => setOpen((value) => !value)}
    >
      <pre
        className={`whitespace-pre-wrap break-words text-[10px] leading-relaxed font-mono max-h-48 overflow-y-auto py-1 ${
          tone === 'muted' ? 'text-on-surface-variant' : 'text-on-surface'
        }`}
      >
        {content}
      </pre>
    </DisclosureRow>
  );
}

function HybridExecutionDetails({
  events,
  rawOutput,
  t,
  forceVisible = false,
}: {
  events?: OutputEvent[];
  rawOutput?: string;
  t: (key: string) => string;
  forceVisible?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const hiddenEvents = (events ?? []).filter(
    (event) => !event.visible && event.type !== 'boundary_marker',
  );
  const sectionCount = hiddenEvents.length + (rawOutput ? 1 : 0);
  const hasDetails = sectionCount > 0;
  if (!forceVisible && !hasDetails) {
    return null;
  }

  return (
    <div className="mt-2.5 border-t border-outline-variant/15 pt-2">
      <DisclosureRow
        label={t('View execution details')}
        meta={sectionCount > 0 ? `${sectionCount}` : undefined}
        open={open}
        onToggle={() => setOpen((value) => !value)}
      >
        <div className="space-y-0.5 py-0.5">
          {hiddenEvents.length === 0 ? (
            <p className="text-[10px] text-on-surface-variant py-1">
              {t('No structured execution details were captured for this turn.')}
            </p>
          ) : (
            hiddenEvents.map((event, index) => (
              <ExecutionDetailBlock
                key={`${event.type}-${index}`}
                label={outputEventLabel(event.type, t)}
                content={event.content}
                tone={event.type === 'shell_echo' ? 'muted' : 'default'}
              />
            ))
          )}
          {rawOutput ? (
            <ExecutionDetailBlock
              label={t('Raw shell output')}
              content={rawOutput}
              tone="muted"
            />
          ) : null}
        </div>
      </DisclosureRow>
    </div>
  );
}

interface ChatFeedProps {
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
  onStopRun?: () => void;
  onContinueRun?: () => void;
  isMultiAgent?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onRetryWithInstructions?: (instructions: string) => void;
  /** D4: answer ask_user_question by picking a card option. */
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
  // New props for ChatInputBar
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
  /** Authorized workspace path — fallback for native terminal resume commands. */
  workspacePath?: string;
  /** Opened from sidebar history — hide chat/terminal toggle, show read-only chrome. */
  isHistorySessionView?: boolean;
  /** Resolve + open a workspace file (or basename) in the App preview overlay. */
  onOpenWorkspaceFile?: (path: string) => void;
  /** Preview an in-memory code snippet (fenced blocks). */
  onPreviewSnippet?: (name: string, content: string) => void;
  /** D51 — Chat shell / execute step → Terminal sync. */
  onViewToolStepInTerminal?: (step: ToolStep) => void;
  /** D30 — switch session from overview board. */
  onSelectSession?: (session: SessionRecord) => void;
  /** D40 — Hub MCP binding badge for Clutch Agent. */
  mcpServerIds?: string[];
  showMcpBindingBadge?: boolean;
  onOpenMcpBind?: () => void;
  /** D18 slash commands */
  onSlashCommand?: (id: import('../services/slashCommands').SlashCommandId) => void | Promise<void>;
  slashNotice?: string | null;
}

const WORKFLOW_AGENTS = new Set(['Builder', 'Orchestrator', 'Evaluator', 'Supervisor']);

function isPlainLlmSession(
  selectedWorkflowId: string | null | undefined,
  activeWorkflowId: string | undefined,
): boolean {
  return !selectedWorkflowId && !activeWorkflowId;
}

function isPlainLlmReply(agent: string): boolean {
  return agent !== 'User' && agent !== 'System' && !WORKFLOW_AGENTS.has(agent);
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

function replyRuntimeLabel(
  runtimeEngine: string | undefined,
  fallbackModelName: string,
): string {
  return runtimeEngine?.trim() || fallbackModelName || '—';
}

const IMAGE_MARKER_RE = /\[image:\s*(data:image\/[^\]]+)\]\s*/gi;
const VIDEO_MARKER_RE = /\[video:\s*((?:https?:\/\/|\/api\/)[^\]]+)\]\s*/gi;
const MD_IMAGE_RE = /!\[([^\]]*)\]\(([^)]+)\)/g;
const MD_IMAGE_LINK_RE = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;

function parseMessageImages(text: string): { text: string; images: string[] } {
  const images: string[] = [];
  const stripped = text.replace(IMAGE_MARKER_RE, (_, url: string) => {
    images.push(url.trim());
    return '';
  }).trim();
  return { text: stripped, images };
}

function parseMarkdownImages(text: string): { text: string; images: Array<{ src: string; alt: string }> } {
  const images: Array<{ src: string; alt: string }> = [];
  const stripped = text.replace(MD_IMAGE_RE, (_, alt: string, url: string) => {
    images.push({ src: url.trim(), alt: alt.trim() || 'generated image' });
    return '';
  });
  const imageUrls = new Set(images.map((image) => image.src));
  const withoutCompanionLinks = stripped.replace(MD_IMAGE_LINK_RE, (match, _alt: string, url: string) => {
    if (imageUrls.has(url.trim())) {
      return '';
    }
    return match;
  });
  return { text: withoutCompanionLinks.replace(/\n{3,}/g, '\n\n').trim(), images };
}

function dedupeImages(images: Array<{ src: string; alt: string }>): Array<{ src: string; alt: string }> {
  const seen = new Set<string>();
  return images.filter((image) => {
    if (seen.has(image.src)) return false;
    seen.add(image.src);
    return true;
  });
}

function parseMessageVideos(text: string): { text: string; videos: Array<{ src: string; title: string }> } {
  const videos: Array<{ src: string; title: string }> = [];
  const stripped = text.replace(VIDEO_MARKER_RE, (_, url: string) => {
    videos.push({ src: url.trim(), title: 'Generated video' });
    return '';
  }).trim();
  return { text: stripped, videos };
}

function parseChatContent(text: string): {
  text: string;
  images: Array<{ src: string; alt: string }>;
  videos: Array<{ src: string; title: string }>;
} {
  const fromVideos = parseMessageVideos(text);
  const fromMarkers = parseMessageImages(fromVideos.text);
  const fromMarkdown = parseMarkdownImages(fromMarkers.text);
  return {
    text: fromMarkdown.text,
    images: dedupeImages([
      ...fromMarkers.images.map((src) => ({ src, alt: 'Attached screenshot' })),
      ...fromMarkdown.images,
    ]),
    videos: fromVideos.videos,
  };
}

function ChatBubbleImage({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <a
        href={src}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 text-[12px] text-primary font-medium hover:underline"
      >
        <LegacyIcon name="image" className="text-[16px]" />
        {alt}
      </a>
    );
  }
  return (
    <a
      href={src}
      target="_blank"
      rel="noopener noreferrer"
      className="block w-full max-w-lg"
      title={alt}
    >
      <img
        src={src}
        alt={alt}
        onError={() => setFailed(true)}
        className="block w-full h-auto max-h-[min(24rem,70vh)] rounded-xl border border-outline-variant/30 object-contain bg-white shadow-sm"
      />
    </a>
  );
}


export const ChatFeed: React.FC<ChatFeedProps> = ({
  messages,
  hybridExecutions,
  inputValue,
  setInputValue,
  onSendMessage,
  clutchStatus,
  currentFlowName = '',
  selectedSidebarWidth,
  rightSidebarWidth,
  sidebarOpen = true,
  rightPanelOpen = true,
  onStopRun,
  onContinueRun,
  isMultiAgent = true,
  onApprove,
  onReject,
  onRetryWithInstructions,
  onAnswerQuestion,
  workspaceAuthorized = false,
  onPickWorkspace,
  onOpenWorkflows,
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
  activeAgentType = '',
  workspaceViewMode,
  onWorkspaceViewModeChange,
  onLeaveTerminalConfirm,
  highlightedDispatchEntryId = null,
  hasCliAgents = false,
  workspaceFiles = [],
  sessions = [],
  skills = [],
  permissionMode = 'ask',
  onPermissionModeChange,
  shellSessionStatus,
  shellPoolBlockerRunIds = [],
  shellPoolBlockers = [],
  shellPoolQueuePosition = 0,
  shellPoolQueueDepth = 0,
  userAvatar,
  userName = 'User',
  terminalLogs = [],
  onClearTerminal,
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
}) => {
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
  /** Input bar + footer clearance reserved under terminal content. */
  const terminalInputReservePx = terminalBarHeight + APP_INPUT_DOCK_BOTTOM_PX;
  /** Gap (1× bar) + input reserve — drives xterm refit when dock chrome changes. */
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

  const handleStopWithQueueClear = useCallback(() => {
    setPendingMessages([]);
    onStopRun?.();
  }, [onStopRun]);

  // Serialize attachments into text for sending
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
    (isRunning && lastUserIndex >= 0 && lastUserIndex > lastAgentIndex && isPlainLlmChat) ||
    showWorkflowThinking;

  const pendingToolSteps = clutchOrchestraState.pending_tool_steps;
  const liveTodos = (clutchOrchestraState.agent_todos ?? []) as TodoItem[];
  const liveGoal = clutchOrchestraState.agent_goal as AgentGoal | undefined;
  const showGoalBar = shouldShowGoalBar(liveGoal);
  const liveSubtasks = (clutchOrchestraState.pending_subtasks ?? []) as SubtaskCard[];
  const bgJobs = (clutchOrchestraState.bg_jobs ?? []) as BackgroundJob[];
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

  /** Pin live todos while incomplete; unpin when all checked so the sealed card scrolls with history. */
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

  const chatScrollBottomPad = useMemo(
    () =>
      dockClearance +
      (showThinking ? thinkingHeight + 16 : 0) +
      // Live activity sits above the fixed dock while awaiting — keep extra room.
      (awaitingHuman && showLiveActivity && !showThinking ? 12 : 0),
    [dockClearance, showThinking, thinkingHeight, awaitingHuman, showLiveActivity],
  );

  const scrollChatToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    bottomRef.current?.scrollIntoView({ behavior, block: 'end' });
  }, []);

  useEffect(() => {
    scrollChatToBottom();
  }, [messages, clutchStatus, showThinking, pendingMessages.length, scrollChatToBottom]);

  useEffect(() => {
    if (!showThinking) return;
    scrollChatToBottom();
  }, [chatScrollBottomPad, showThinking, scrollChatToBottom]);

  useEffect(() => {
    const dock = dockRef.current;
    if (!dock || showTerminalWorkspace) return;
    const measure = () => {
      setDockClearance(
        APP_INPUT_DOCK_BOTTOM_PX + dock.offsetHeight + CHAT_SCROLL_ABOVE_DOCK_GAP_PX,
      );
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
  ]);

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

  const renderAgentLabel = (
    agent: string,
    statusHint?: string,
    runtimeEngine?: string,
    workflowAgentType?: string,
  ) => {
    const showPlainLlmLabel = isPlainLlmChat && isPlainLlmReply(agent);
    const showHybridLabel = Boolean(runtimeEngine?.includes('Hybrid'));
    const showWorkflowLabel = !isPlainLlmChat && Boolean(workflowAgentType);

    if (showPlainLlmLabel || (statusHint && isPlainLlmChat) || showHybridLabel || showWorkflowLabel) {
      const agentTitle = showHybridLabel ? agent : (agent || activeAgentName || t('Clutch Agent'));
      const engineLabel = showHybridLabel
        ? replyRuntimeLabel(runtimeEngine, llmModelName)
        : workflowAgentType
          ? workflowAgentType
          : statusHint
            ? replyRuntimeLabel(engineHint, llmModelName)
            : replyRuntimeLabel(runtimeEngine, llmModelName);
      return (
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-bold text-on-surface leading-tight">{agentTitle}</span>
            {engineLabel && (
              <span className="text-[10px] text-on-surface-variant/60 leading-tight truncate uppercase tracking-wide">
                {engineLabel}
              </span>
            )}
          </div>
          {statusHint && (
            <span className="text-[10px] text-on-surface-variant/60 flex-shrink-0">{statusHint}</span>
          )}
        </div>
      );
    }

    return (
      <>
        <span className="text-xs font-bold text-on-surface">{agent}</span>
        {statusHint && (
          <span className="text-[10px] text-on-surface-variant/60">{statusHint}</span>
        )}
      </>
    );
  };

  const workspaceChromeRowClass = (extra = '') =>
    `flex justify-end shrink-0 ${isTerminalLayout ? 'mb-3' : 'mb-6'} ${extra}`.trim();

  const workspaceChromeRowStyle = { paddingTop: WORKSPACE_CHROME_ROW_TOP_PX };

  return (
  <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden relative w-full">
    <section
      style={{
        paddingLeft: `${leftChromePad}px`,
        paddingRight: `${rightChromePad}px`,
        paddingTop: APP_HEADER_HEIGHT_PX,
        paddingBottom: isTerminalLayout
          ? terminalInputReservePx
          : Math.max(chatScrollBottomPad, awaitingHuman ? 200 : 120),
      }}
      className={`flex-1 min-h-0 flex flex-col box-border transition-all duration-300 bg-background ${
        isTerminalLayout
          ? 'overflow-hidden pb-1 items-stretch px-4'
          : `overflow-y-auto overscroll-contain items-stretch ${chatChrome.chatEdgePaddingClass}`
      }`}
    >
      <div
        className={`w-full min-w-0 ${
          isTerminalLayout
            ? 'flex-1 min-h-0 flex flex-col max-w-none h-full'
            : `${chatChrome.chatMaxWidthClass} mx-auto ${chatChrome.messageListSpacingClass} py-4`
        }`}
      >
        {showWorkspaceReadonlyChrome ? (
          <div className={workspaceChromeRowClass()} style={workspaceChromeRowStyle}>
            <span
              data-testid="workspace-view-readonly-label"
              className="inline-flex items-center gap-1.5 rounded-xl border border-outline-variant/40 px-3 py-1.5 text-[11px] font-bold whitespace-nowrap shadow-sm bg-surface-container-low text-on-surface-variant"
            >
              {t('Chat mode')}
              <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-neutral-100 text-on-surface-variant/80">
                {t('Read-only')}
              </span>
            </span>
          </div>
        ) : showWorkspaceViewToggle ? (
          <div
            className={workspaceChromeRowClass()}
            style={workspaceChromeRowStyle}
          >
            <div
              data-testid="workspace-view-toggle"
              className="inline-flex items-center rounded-xl border border-outline-variant/40 overflow-hidden text-xs font-bold whitespace-nowrap shadow-sm bg-surface-container-low"
            >
              <button
                type="button"
                data-testid="workspace-view-chat"
                onClick={() => handleWorkspaceViewChange('chat')}
                className={`inline-flex items-center justify-center px-3 h-7 text-[11px] leading-none transition-colors ${
                  workspaceViewMode === 'chat'
                    ? 'bg-neutral-900 text-white'
                    : 'bg-transparent text-on-surface-variant hover:bg-surface-container-high'
                }`}
              >
                {t('Chat mode')}
              </button>
              <button
                type="button"
                data-testid="workspace-view-terminal"
                onClick={() => handleWorkspaceViewChange('terminal')}
                className={`inline-flex items-center justify-center px-3 h-7 text-[11px] leading-none transition-colors border-l border-outline-variant/40 ${
                  workspaceViewMode === 'terminal'
                    ? 'bg-neutral-900 text-white'
                    : 'bg-transparent text-on-surface-variant hover:bg-surface-container-high'
                }`}
              >
                {t('Terminal mode')}
              </button>
            </div>
          </div>
        ) : null}
        {workspaceViewMode === 'chat' && showEmptyState && (
          <div className="flex flex-col items-center justify-center text-center py-16 px-6 space-y-5">
            <div className="w-14 h-14 rounded-2xl bg-surface-container-low border border-outline-variant/40 flex items-center justify-center">
              <LegacyIcon name={isMultiAgent ? "hub" : "smart_toy"} className="text-[28px] text-on-surface-variant" />
            </div>
            <div className="space-y-2 max-w-md">
              <h2
                data-testid="chat-supervised-title"
                className="text-lg font-bold text-on-surface tracking-tight"
              >
                {isMultiAgent ? t('Start a supervised session') : t('Start a single agent session')}
              </h2>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                {isMultiAgent
                  ? t('Select a workspace and start a workflow, or type an instruction below. Clutch will orchestrate AI Agents and ask for your approval when needed.')
                  : t('Select a workspace and type an instruction below to chat with the agent directly.')
                }
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {workspacePickError && (
                <p className="w-full text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                  {workspacePickError}
                </p>
              )}
              {!workspaceAuthorized && (
                <button
                  type="button"
                  data-testid="chat-authorize-workspace"
                  onClick={onPickWorkspace}
                  className={`${BTN_PRIMARY}`}
                >
                  {t('Authorize workspace')}
                </button>
              )}
              {workspaceAuthorized && isMultiAgent && (
                <button
                  type="button"
                  data-testid="chat-open-workflows"
                  onClick={onOpenWorkflows}
                  className={BTN_SECONDARY}
                >
                  {t('Choose workflow')}
                </button>
              )}
            </div>
          </div>
        )}

        {keepTerminalMounted ? (
          <div
            ref={terminalStageRef}
            className={isTerminalLayout ? 'flex flex-1 flex-col min-h-0 min-w-0 w-full' : undefined}
            style={isTerminalLayout ? undefined : XTERM_KEEPALIVE_STYLE}
            aria-hidden={isTerminalLayout ? undefined : true}
          >
            <TerminalOrchestraWorkspace
              visible={isTerminalLayout}
              clutchStatus={clutchStatus}
              sessionRunId={sessionRunId}
              barFocused={orchestratorBarFocused}
              configuredAgents={mentionableAgents}
              sessionDispatched={sessionDispatched}
              previewAgentType={terminalPreviewAgentType}
              previewAgentId={sessionDispatched ? null : inputTerminalMention?.agentId ?? null}
              previewAgentName={sessionDispatched ? null : inputTerminalMention?.name ?? null}
              layoutChromeKey={terminalLayoutChromeKey}
              layoutObserveRef={terminalStageRef}
              onOpenWorkspaceFile={onOpenWorkspaceFile}
            />
          </div>
        ) : isPlainLlmChat && hasCliAgents && isTerminalLayout ? (
          <TerminalOrchestraEmptyState sessionRunId={sessionRunId} />
        ) : null}

        {isTerminalLayout ? (
          <div
            data-testid="terminal-input-gap"
            className="shrink-0 w-full"
            style={{ height: terminalBarHeight }}
            aria-hidden
          />
        ) : null}

        {isTerminalDispatchHistoryReadonly ? (
          <div className={`w-full ${chatChrome.chatMaxWidthClass} mx-auto ${chatChrome.messageListSpacingClass} py-4`}>
            <TerminalDispatchHistoryFeed
              entries={clutchOrchestraState.dispatch_log ?? []}
              highlightedEntryId={highlightedDispatchEntryId}
              userAvatar={userAvatar}
              userName={userName}
              mentionableAgents={mentionableAgents}
              workspacePath={workspacePath}
              onOpenWorkspaceFile={onOpenWorkspaceFile}
            />
          </div>
        ) : null}

        {workspaceViewMode === 'chat' && messages.map((msg, messageIndex) => {
          const isUser = msg.agent === 'User';
          const replyStepIndex = workflowReplyStepIndex.get(msg.id);
          const replyStep = replyStepIndex !== undefined
            ? workflowAgentSteps[replyStepIndex]
            : undefined;
          const workflowReplyType = !isPlainLlmChat && !isUser
            ? (msg.runtimeEngine?.trim()
              ? replyRuntimeLabel(msg.runtimeEngine, llmModelName)
              : replyStep?.agentType || '')
            : undefined;
          const assistantContent = !isUser
            ? resolveAssistantContentSource(msg, hybridExecutions)
            : null;
          const parsed = parseChatContent(
            isUser ? msg.text : (assistantContent?.parseSource ?? msg.text),
          );
          const displayText = isUser ? parsed.text : (assistantContent?.displayText ?? parsed.text);
          const isErrorMsg =
            msg.status === 'FAILED' ||
            msg.badgeText?.includes('FAILED') ||
            msg.badgeText?.includes('NEEDS');
          const isCompletedMsg = msg.status === 'COMPLETED';
          const isWorkflowMeta = msg.agent === 'Evaluator' || msg.agent === 'Supervisor' || msg.agent === 'Builder';
          const avatarUrl = isUser
            ? (userAvatar || USER_CHAT_AVATAR)
            : isWorkflowMeta
              ? (resolveBrandLogoSrc({ toolId: 'rivet-cli' }) || USER_CHAT_AVATAR)
              : (
                msg.avatar
                || resolveBrandLogoSrc({ toolId: replyStep?.toolId, runtimeEngine: msg.runtimeEngine })
                || resolveAgentLogo?.(msg.agent)
              );

          // Cursor-style: inline per-edit Diff cards render as standalone feed blocks (no empty bubble).
          const isInlineDiffOnly =
            !isUser &&
            Boolean(msg.diffSummary?.inline) &&
            !(displayText || '').trim() &&
            !msg.planCard &&
            !msg.questionCard &&
            !msg.verificationReport &&
            !(msg.todoList && msg.todoList.length > 0) &&
            !(msg.toolSteps && msg.toolSteps.length > 0);

          if (isInlineDiffOnly && msg.diffSummary) {
            return (
              <div
                key={msg.id}
                className="w-full flex justify-start pl-10"
                onContextMenu={(e) => handleMessageContextMenu(e, msg.id, messageIndex)}
              >
                <div className="min-w-0 max-w-[min(100%,36rem)] flex-1">
                  <DiffSummaryCardView
                    summary={msg.diffSummary}
                    t={t}
                    onOpenFile={onOpenWorkspaceFile}
                  />
                </div>
              </div>
            );
          }

          return (
            <div
              key={msg.id}
              className={`w-full flex ${isUser ? 'justify-end' : 'justify-start'}`}
              onContextMenu={(e) => handleMessageContextMenu(e, msg.id, messageIndex)}
            >
              <div
                className={`${chatChrome.messageRowClass} ${
                  isUser ? 'flex-row-reverse' : ''
                }`}
              >
                {isUser ? (
                  <div className={`${chatChrome.messageAvatarClass} rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center ${avatarUrl === clutchMarkUrl ? 'bg-black' : 'bg-surface-container'}`}>
                    {avatarUrl ? (
                      <img
                        className={avatarUrl === clutchMarkUrl ? 'w-full h-full object-cover' : 'w-full h-full object-contain p-1'}
                        src={avatarUrl}
                        alt={msg.agent}
                      />
                    ) : (
                      <LegacyIcon name="person" className="text-[18px] text-on-surface-variant" />
                    )}
                  </div>
                ) : (
                  <AgentChatAvatar
                    src={avatarUrl}
                    alt={msg.agent}
                    fallbackIcon={
                      msg.agent === 'Supervisor'
                        ? 'verified_user'
                        : msg.agent === 'Evaluator'
                          ? 'gavel'
                          : msg.agent === 'System'
                            ? 'info'
                            : 'smart_toy'
                    }
                  />
                )}

                <div className="flex-1 space-y-1.5 min-w-0">
                  <div className={`flex items-center gap-2 ${isUser ? 'justify-end' : ''}`}>
                    {isUser ? (
                      <>
                        <span className="text-[10px] text-on-surface-variant/60">{msg.time}</span>
                        <span className="text-xs font-bold text-on-surface">{userName || msg.agent}</span>
                      </>
                    ) : (
                      <div className={`flex items-center gap-2 ${isPlainLlmChat && isPlainLlmReply(msg.agent) ? 'items-start' : ''}`}>
                        {renderAgentLabel(msg.agent, undefined, msg.runtimeEngine, workflowReplyType)}
                        <span className="text-[10px] text-on-surface-variant/60 flex-shrink-0">{msg.time}</span>
                      </div>
                    )}
                  </div>

                  {isErrorMsg ? (
                    <div className={`${chatChrome.messageBubblePaddingClass} bg-neutral-50/50 rounded-2xl rounded-tl-none border border-neutral-200/80 shadow-xs`}>
                      <div className="flex items-center gap-1.5 mb-2 text-neutral-800 font-bold text-[11px]">
                        <LegacyIcon name="error" className="text-[16px]" />
                        <span>VALIDATION FAILED</span>
                      </div>
                      {renderMarkdown(msg.text)}
                    </div>
                  ) : (
                    <div
                      className={`${chatChrome.messageBubblePaddingClass} rounded-2xl border border-outline-variant/30 shadow-sm ${
                      isUser 
                        ? 'bg-primary/10 text-on-surface rounded-tr-none text-left' 
                        : 'bg-surface-container-low rounded-tl-none'
                    }`}>
                      {msg.badgeText ? (
                        <div className="flex items-center gap-1.5 mb-2 text-primary font-bold text-[11px]">
                          <LegacyIcon name="info" className="text-[16px]" />
                          <span>{msg.badgeText}</span>
                        </div>
                      ) : isCompletedMsg ? (
                        <div className="flex items-center gap-1.5 mb-2 text-green-600 font-bold text-[11px]">
                          <LegacyIcon name="check_circle" className="text-[16px]" />
                          <span>COMPLETED</span>
                        </div>
                      ) : null}

                      {!isUser && !msg.planCard && !msg.questionCard && msg.toolSteps && msg.toolSteps.length > 0 ? (
                        <AgentLiveActivity
                          steps={msg.toolSteps}
                          className="mb-2"
                          onOpenFile={onOpenWorkspaceFile}
                          onViewInTerminal={onViewToolStepInTerminal}
                        />
                      ) : null}

                      {parsed.images.length > 0 && (
                        <div className="flex flex-col gap-2 mb-3">
                          {parsed.images.map((image, index) => (
                            <ChatBubbleImage
                              key={`${msg.id}-img-${index}`}
                              src={image.src}
                              alt={image.alt}
                            />
                          ))}
                        </div>
                      )}
                      {parsed.videos.length > 0 && (
                        <div className="flex flex-col gap-3 mb-3">
                          {parsed.videos.map((video, index) => (
                            <ChatBubbleVideo
                              key={`${msg.id}-vid-${index}`}
                              src={video.src}
                              title={t(video.title)}
                            />
                          ))}
                        </div>
                      )}
                      {/* Plan / question cards own the bubble — skip duplicate prose. */}
                      {!msg.planCard && !msg.questionCard && renderMarkdown(displayText)}
                      {!isUser && (() => {
                        const hybridMeta = hybridExecutions?.[msg.id];
                        const executionEvents = hybridMeta?.outputEvents ?? msg.outputEvents;
                        const executionRaw = hybridMeta?.rawOutput ?? msg.rawOutput;
                        const showDetails =
                          isHybridReply(msg) ||
                          Boolean(executionEvents?.length) ||
                          Boolean(executionRaw);
                        if (!showDetails) return null;
                        return (
                          <HybridExecutionDetails
                            events={executionEvents}
                            rawOutput={executionRaw}
                            t={t}
                            forceVisible={isHybridReply(msg)}
                          />
                        );
                      })()}
                      {!isUser &&
                      msg.filesChanged &&
                      msg.filesChanged.length > 0 &&
                      !(msg.toolSteps || []).some((step) => Boolean(step.fileDiff)) ? (
                        <FilesChangedChips
                          paths={msg.filesChanged}
                          onOpen={onOpenWorkspaceFile}
                          label={t('Changed files')}
                        />
                      ) : null}
                      {!isUser && msg.planCard ? (
                        <PlanCardView
                          card={msg.planCard}
                          t={t}
                          stepComments={
                            awaitingPlan && msg === pendingPlanMessage
                              ? planStepComments
                              : undefined
                          }
                          onStepCommentChange={
                            awaitingPlan && msg === pendingPlanMessage
                              ? (index, value) => {
                                  setPlanStepComments((prev) => {
                                    const next = [...prev];
                                    next[index] = value;
                                    return next;
                                  });
                                }
                              : undefined
                          }
                        />
                      ) : null}
                      {!isUser && msg.questionCard ? (
                        <QuestionCardView
                          card={msg.questionCard}
                          t={t}
                          interactive={
                            awaitingHuman &&
                            msg.questionCard.status === 'pending' &&
                            pendingQuestionMessage?.id === msg.id
                          }
                          onSelect={(option) => {
                            if (hitlBusy) return;
                            setHitlBusy(true);
                            onAnswerQuestion?.(option);
                          }}
                        />
                      ) : null}
                      {!isUser && msg.todoList && msg.todoList.length > 0 ? (
                        <TodoCardView todos={msg.todoList} t={t} />
                      ) : null}
                      {!isUser && msg.subtaskCards && msg.subtaskCards.length > 0 ? (
                        <SubtaskCardView
                          cards={msg.subtaskCards}
                          t={t}
                          onViewInTerminal={onViewToolStepInTerminal}
                        />
                      ) : null}
                      {!isUser && msg.verificationReport ? (
                        <VerificationReportCardView
                          report={msg.verificationReport}
                          t={t}
                          onOpenChangedFile={onOpenWorkspaceFile}
                        />
                      ) : null}
                      {!isUser &&
                      msg.diffSummary &&
                      !(msg.toolSteps || []).some((step) => Boolean(step.fileDiff)) ? (
                        <DiffSummaryCardView
                          summary={msg.diffSummary}
                          t={t}
                          onOpenFile={onOpenWorkspaceFile}
                        />
                      ) : null}
                      {msg.codeHighlight && (
                        <div className="mt-3 flex items-center gap-2 py-2 px-3 bg-white/60 rounded-xl border border-outline-variant/30">
                          <LegacyIcon name="check_circle" className="text-green-500 text-[18px]" />
                          <span className="text-[11px] font-semibold text-on-surface">
                            {msg.codeHighlight.lineCount} files updated in {msg.codeHighlight.file}
                          </span>
                        </div>
                      )}
                      {(msg.executionTime || msg.tokens) && (
                        <div className="mt-3 pt-3 border-t border-outline-variant/10 flex gap-4 text-[9px] text-on-surface-variant/60 font-mono">
                          {msg.executionTime && <span>{msg.executionTime}</span>}
                          {msg.tokens && <span>{msg.tokens}</span>}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {workspaceViewMode === 'chat' && showThinking && (
          <div ref={thinkingRef} className="w-full flex justify-start mb-4">
            <div className={chatChrome.thinkingRowClass}>
              <AgentChatAvatar
                src={thinkingAgentLogo || activeAgentAvatar}
                alt={thinkingAgentName || t('Clutch Agent')}
              />

              <div className="flex-1 space-y-1.5 min-w-0">
                <div className="flex items-center gap-2">
                  {renderAgentLabel(
                    thinkingAgentName || t('Clutch Agent'),
                    shellSessionStatus === 'queued_pool'
                      ? t('Queued for shell...')
                      : showLiveActivity
                        ? t('Working…')
                        : t('Thinking...'),
                    isPlainLlmChat ? undefined : engineHint,
                    thinkingAgentType || undefined,
                  )}
                </div>

                {showLiveActivity ? (
                  <div
                    className={`${chatChrome.thinkingBubblePaddingClass} bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 shadow-sm`}
                  >
                    <AgentLiveActivity
                      steps={liveActivitySteps}
                      reasoningContent={liveReasoning}
                      live
                      defaultOpen
                      onOpenFile={onOpenWorkspaceFile}
                      onViewInTerminal={onViewToolStepInTerminal}
                    />
                    {showInlineLiveTodos ? (
                      <TodoCardView todos={liveTodos} t={t} live />
                    ) : null}
                    {liveSubtasks.length > 0 ? (
                      <SubtaskCardView
                        cards={liveSubtasks}
                        t={t}
                        live
                        onViewInTerminal={onViewToolStepInTerminal}
                      />
                    ) : null}
                  </div>
                ) : (
                  <div
                    className={`${chatChrome.thinkingBubblePaddingClass} bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 shadow-sm flex items-center gap-1.5 min-h-9`}
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-on-surface/40 animate-typing-pulse" />
                    <div className="w-1.5 h-1.5 rounded-full bg-on-surface/40 animate-typing-pulse animation-delay-100" />
                    <div className="w-1.5 h-1.5 rounded-full bg-on-surface/40 animate-typing-pulse animation-delay-200" />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {workspaceViewMode === 'chat' && !showThinking && showLiveActivity && awaitingHuman ? (
          <div className="w-full flex justify-start mb-4">
            <div className={chatChrome.thinkingRowClass}>
              <div className="w-8 shrink-0" aria-hidden />
              <div className="flex-1 overflow-hidden">
                <div
                  className={`${chatChrome.thinkingBubblePaddingClass} bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 shadow-sm`}
                >
                  <AgentLiveActivity
                    steps={liveActivitySteps}
                    reasoningContent={liveReasoning}
                    live
                    defaultOpen
                    onOpenFile={onOpenWorkspaceFile}
                    onViewInTerminal={onViewToolStepInTerminal}
                  />
                  {showInlineLiveTodos ? (
                    <TodoCardView todos={liveTodos} t={t} live />
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {workspaceViewMode === 'chat' ? (
          <div ref={bottomRef} style={{ scrollMarginBottom: chatScrollBottomPad }} className="h-2 shrink-0" aria-hidden />
        ) : null}
      </div>

    </section>

    {/* D29 — active session goal bar */}
    {workspaceViewMode === 'chat' && showGoalBar && liveGoal ? (
      <div
        data-testid="goal-sticky-rail"
        className={`pointer-events-none absolute z-25 ${chatChrome.chatEdgePaddingClass}`}
        style={{
          top: APP_HEADER_HEIGHT_PX + (pinLiveTodos ? 72 : 0),
          left: leftChromePad,
          right: rightChromePad,
        }}
      >
        <div className="bg-background pt-2">
          <div className={`pointer-events-auto mx-auto w-full ${chatChrome.chatMaxWidthClass}`}>
            <GoalBarView goal={liveGoal} t={t} />
          </div>
        </div>
      </div>
    ) : null}

    {/* Incomplete live todos: pin under header with an opaque curtain (no scroll bleed). */}
    {workspaceViewMode === 'chat' && pinLiveTodos ? (
      <div
        data-testid="todo-sticky-rail"
        className={`pointer-events-none absolute z-30 ${chatChrome.chatEdgePaddingClass}`}
        style={{
          top: APP_HEADER_HEIGHT_PX,
          left: leftChromePad,
          right: rightChromePad,
        }}
      >
        <div className="bg-background pt-3">
          <div className={`pointer-events-auto mx-auto w-full ${chatChrome.chatMaxWidthClass}`}>
            <TodoCardView todos={liveTodos} t={t} live pinned />
          </div>
        </div>
        {/* Fade into the scrolling feed so content disappears cleanly under the pin. */}
        <div
          className="h-4 bg-gradient-to-b from-background via-background/80 to-transparent"
          aria-hidden
        />
      </div>
    ) : null}

    <div
        ref={showTerminalWorkspace ? terminalDockRef : dockRef}
        data-testid={showTerminalWorkspace ? 'terminal-orchestrator-dock' : undefined}
        style={{
          left: `${leftChromePad - 6}px`,
          right: `${rightChromePad - 6}px`,
          bottom: APP_INPUT_DOCK_BOTTOM_PX,
        }}
        className={`fixed flex justify-center ${chatChrome.chatEdgePaddingClass} z-40 transition-all duration-300 select-none`}
      >
        {showTerminalWorkspace ? (
          <div ref={terminalBarRef} className={`w-full ${chatChrome.chatMaxWidthClass}`}>
            <OrchestratorBar
            sessionRunId={sessionRunId}
            drafts={clutchOrchestraState.pending_handoff_drafts ?? []}
            inputValue={inputValue}
            setInputValue={setInputValue}
            permissionMode={permissionMode}
            onPermissionModeChange={onPermissionModeChange ?? (() => {})}
            workspaceFiles={workspaceFiles}
            sessions={sessions}
            skills={skills}
            onFocusChange={setOrchestratorBarFocused}
            mentionableAgents={mentionableAgents}
            selectedMentionAgentId={selectedMentionAgentId}
            onMentionAgentChange={onMentionAgentChange}
          />
          </div>
        ) : isRunning && !awaitingHuman && !isPlainLlmChat && !isRefining ? (
          <div className={`w-full ${chatChrome.chatMaxWidthClass} bg-white border border-outline-variant p-3 shadow-xl rounded-xl flex items-center justify-between`}>
            <div className="flex items-center gap-3">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-black" />
              </span>
              <div className="text-left">
                <p className="text-[10px] font-bold tracking-wider text-on-surface-variant uppercase">
                  {t('Workflow running')}
                  {currentFlowName ? ` · ${currentFlowName}` : ''}
                </p>
                <p className="text-xs text-on-surface mt-0.5 font-medium">
                  {t('Receiving sidecar events')}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onStopRun}
              className="px-3.5 py-1.5 bg-neutral-900 hover:bg-black text-white font-bold rounded-lg text-[10px] uppercase tracking-wider flex items-center gap-1.5"
            >
              <LegacyIcon name="cancel" className="text-[13px]" />
              Stop
            </button>
          </div>
        ) : awaitingHuman ? (
          <div className={`w-full ${chatChrome.chatMaxWidthClass} flex flex-col gap-1.5`}>
            <div
              className="flex items-center gap-2 rounded-xl border border-outline-variant/30 bg-white px-2.5 py-1.5 shadow-sm"
              role="group"
              aria-label={
                awaitingQuestion
                  ? t('Awaiting your choice')
                  : awaitingPlan
                    ? t('Awaiting plan approval')
                    : t('Needs approval')
              }
            >
              <span className="text-[11px] text-on-surface-variant shrink-0 truncate font-medium">
                {awaitingQuestion
                  ? t('Pick an option in the question card above')
                  : awaitingPlan
                    ? t('Awaiting plan approval')
                    : t('Needs approval')}
              </span>
              <div className="ml-auto flex items-center gap-1.5 shrink-0">
                {!awaitingQuestion ? (
                  <button
                    type="button"
                    data-testid="chat-approve"
                    disabled={hitlBusy}
                    onClick={() => {
                      setHitlBusy(true);
                      onApprove?.();
                    }}
                    className={`${BTN_SM} bg-neutral-900 hover:bg-black text-white border border-neutral-900`}
                  >
                    {awaitingPlan ? t('Approve plan') : t('Allow')}
                  </button>
                ) : null}
                <button
                  type="button"
                  data-testid="chat-reject"
                  disabled={hitlBusy}
                  onClick={() => {
                    setHitlBusy(true);
                    onReject?.();
                  }}
                  className={`${BTN_SM} bg-neutral-100 hover:bg-neutral-200 text-neutral-800 border border-neutral-200/80`}
                >
                  {awaitingQuestion
                    ? t('Cancel question')
                    : awaitingPlan
                      ? t('Cancel plan')
                      : t('Reject')}
                </button>
              </div>
            </div>
            {(awaitingQuestion
              ? pendingQuestionMessage?.questionCard?.allowCustom !== false
              : true) ? (
              <div className="flex items-center gap-1.5 px-0.5">
                <input
                  type="text"
                  value={hillInstructions}
                  onChange={(e) => setHillInstructions(e.target.value)}
                  disabled={hitlBusy}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      if (awaitingPlan && canSubmitPlanRevise && !hitlBusy) {
                        submitPlanRevise();
                        return;
                      }
                      if (hillInstructions.trim() && !hitlBusy) {
                        setHitlBusy(true);
                        onRetryWithInstructions?.(hillInstructions.trim());
                        setHillInstructions('');
                      }
                    }
                  }}
                  placeholder={
                    awaitingQuestion
                      ? t('Or type your own answer…')
                      : awaitingPlan
                        ? t('Suggest plan changes…')
                        : t('Retry with note…')
                  }
                  className="min-w-0 flex-1 rounded-lg border border-outline-variant/30 bg-surface-container-low px-2.5 py-1.5 text-[11px] text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-1 focus:ring-neutral-900/15"
                />
                <button
                  type="button"
                  disabled={hitlBusy || (awaitingPlan ? !canSubmitPlanRevise : !hillInstructions.trim())}
                  onClick={() => {
                    if (awaitingPlan) {
                      submitPlanRevise();
                      return;
                    }
                    if (hillInstructions.trim() && !hitlBusy) {
                      setHitlBusy(true);
                      onRetryWithInstructions?.(hillInstructions.trim());
                      setHillInstructions('');
                    }
                  }}
                  className={
                    !hitlBusy && (awaitingPlan ? canSubmitPlanRevise : hillInstructions.trim())
                      ? `${BTN_SM} bg-neutral-900 text-white border border-neutral-900`
                      : `${BTN_SM} bg-transparent text-on-surface-variant/40 border border-transparent cursor-not-allowed`
                  }
                >
                  {awaitingQuestion
                    ? t('Submit')
                    : awaitingPlan
                      ? t('Revise')
                      : t('Retry')}
                </button>
              </div>
            ) : null}
          </div>
        ) : isTerminalDispatchHistoryReadonly ? (
          <div className="w-full flex justify-center">
            <OrchestratorBar
              sessionRunId={sessionRunId}
              drafts={[]}
              inputValue=""
              setInputValue={() => {}}
              permissionMode={permissionMode}
              onPermissionModeChange={onPermissionModeChange ?? (() => {})}
              workspaceFiles={workspaceFiles}
              sessions={sessions}
              skills={skills}
              mentionableAgents={mentionableAgents}
              selectedMentionAgentId={selectedMentionAgentId}
              onMentionAgentChange={onMentionAgentChange}
              readOnly
            />
          </div>
        ) : workspaceViewMode === 'chat' ? (
          <div className="w-full flex flex-col items-center">
            {foregroundShell ? (
              <ForegroundShellBar
                shell={foregroundShell}
                t={t}
                onMoveToBackground={() => {
                  void clutchStore.send({ action: 'move_fg_to_background' });
                }}
              />
            ) : null}
            {chatDiagnostics.length ? (
              <DiagnosticsIssuesStrip issues={chatDiagnostics} t={t} />
            ) : null}
            {isPlainLlmChat ? (
              <WorktreeIsolationBar
                worktree={worktreeIsolation}
                t={t}
                onMerge={() => {
                  void clutchStore.send({ action: 'merge_worktree' });
                }}
                onDiscard={() => {
                  void clutchStore.send({ action: 'discard_worktree' });
                }}
              />
            ) : null}
            <BackgroundJobsBar
              jobs={bgJobs}
              t={t}
              onKillJob={(jobId) => {
                void clutchStore.send({ action: 'kill_bg_job', job_id: jobId });
              }}
            />
            {bgJobToast ? (
              <div
                data-testid="bg-job-failure-toast"
                className="w-full max-w-3xl mx-auto px-3 pb-2"
              >
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] font-medium text-rose-800">
                  {bgJobToast}
                </div>
              </div>
            ) : null}
            <ChatInputBar
              inputValue={inputValue}
              setInputValue={setInputValue}
              onSendMessage={handleSendWithAttachments}
              isRunning={isRunning}
              isPlainLlmChat={isPlainLlmChat}
              onStopRun={handleStopWithQueueClear}
              onContinueRun={onContinueRun}
              awaitingContinue={Boolean(clutchOrchestraState.awaiting_continue)}
              runStats={clutchOrchestraState.run_stats}
              sessionTokens={clutchOrchestraState.session_tokens}
              pendingMessages={pendingMessages}
              onRemovePendingMessage={removePending}
              selectedWorkflowId={selectedWorkflowId}
              selectedWorkflowName={selectedWorkflowName}
              onClearSelectedWorkflow={onClearSelectedWorkflow}
              isMultiAgent={isMultiAgent}
              workspaceFiles={workspaceFiles}
              sessions={sessions}
              skills={skills}
              permissionMode={permissionMode}
              onPermissionModeChange={onPermissionModeChange ?? (() => {})}
              shellSessionStatus={shellSessionStatus}
              shellPoolBlockerRunIds={shellPoolBlockerRunIds}
              shellPoolBlockers={shellPoolBlockers}
              shellPoolQueuePosition={shellPoolQueuePosition}
              shellPoolQueueDepth={shellPoolQueueDepth}
              currentRunId={sessionRunId}
              clutchStatus={clutchStatus}
              onSelectSession={onSelectSession}
              resolveAgentLogo={resolveAgentLogo}
              onDismissHybridNotice={() => clutchStore.clearShellSessionNotice()}
              isFlowRefining={isRefining}
              workflowAgents={workflowAgentSteps}
              mentionableAgents={mentionableAgents}
              selectedMentionAgentId={selectedMentionAgentId}
              onMentionAgentChange={onMentionAgentChange}
              mcpServerIds={mcpServerIds}
              showMcpBindingBadge={showMcpBindingBadge}
              onOpenMcpBind={onOpenMcpBind}
              onSlashCommand={onSlashCommand}
              slashNotice={slashNotice}
              onRewindFiles={isPlainLlmChat ? handleRewindFiles : undefined}
              onEnableWorktree={
                isPlainLlmChat
                  ? () => {
                      void clutchStore.send({ action: 'enable_worktree' });
                    }
                  : undefined
              }
              worktreeActive={Boolean(worktreeIsolation?.enabled)}
            />
          </div>
        ) : null}
      </div>
    {messageContextMenu ? (
        <div
          className="fixed bg-surface-bright border border-outline-variant rounded-lg shadow-lg py-1 z-[100] min-w-[120px]"
          style={{ top: messageContextMenu.y, left: messageContextMenu.x }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            className="w-full text-left px-3 py-2 text-xs text-on-surface hover:bg-surface-container-low transition-colors flex items-center gap-2"
            data-testid="fork-session-menu"
            onClick={() => {
              void handleForkSession(messageContextMenu.messageIndex);
              setMessageContextMenu(null);
            }}
          >
            <LegacyIcon name="fork_right" className="text-[16px]" />
            {t('Fork session here')}
          </button>
          <button
            type="button"
            className="w-full text-left px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 hover:text-rose-700 transition-colors flex items-center gap-2"
            onClick={() => {
              deleteChatMessage(messageContextMenu.messageId);
              setMessageContextMenu(null);
            }}
          >
            <LegacyIcon name="delete" className="text-[16px]" />
            {t('Delete message')}
          </button>
        </div>
      ) : null}
  </div>
  );
};
