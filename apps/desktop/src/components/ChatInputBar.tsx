/**
 * ChatInputBar — Rich chat input with:
 *  - Image paste (chip preview with thumbnail)
 *  - File/folder drag-and-drop from right panel (chip with icon)
 *  - + menu: local attach / project file / skill command / session
 *  - Permission mode selector (4 modes, backend-persisted)
 *  - / command → slash commands (D18) + skill picker popover
 *  - # → session picker popover
 */
import React, { useRef, useState, useEffect, useCallback, useMemo } from 'react';
import { Loader2 } from 'lucide-react';
import { useLanguage } from './LanguageContext';
import type { SessionRecord } from '../services/runApi';
import type { ScannedSkill } from '../services/skillsApi';
import type { FileTreeNode } from '../services/workspaceApi';
import { PERMISSION_MODES, CHAT_MODE_PRESETS, type PermissionMode } from '../services/permissionApi';
import { clutchStore } from '../services/clutchState';
import { LegacyIcon } from './ui/LegacyIcon';
import { BTN_ICON_SM } from './ui/buttonStyles';
import { shouldSubmitChatOnEnter } from './chatInputKeyboard';
import { AgentChatAvatar } from './AgentChatAvatar';
import { McpBindingBadge } from './McpBindingBadge';
import { parseInputAgentMention } from '../services/terminalOrchestraUtils';
import {
  filterSlashCommands,
  matchExactSlashCommand,
  type SlashCommand,
  type SlashCommandId,
} from '../services/slashCommands';
import { UsageDashboard } from './UsageDashboard';
import { SessionOverviewBoard } from './SessionOverviewBoard';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface Attachment {
  id: string;
  kind: 'image' | 'file' | 'folder';
  name: string;
  path?: string;         // for file/folder
  dataUrl?: string;      // for image preview
  mimeType?: string;
}

export type { PendingChatMessage } from '../services/chatPendingQueue';
import type { PendingChatMessage } from '../services/chatPendingQueue';
import { queuePositionLabel } from '../services/chatPendingQueue';

export interface ShellPoolBlocker {
  run_id: string;
  title?: string;
  agent_name?: string;
}

interface ChatInputBarProps {
  inputValue: string;
  setInputValue: (val: string) => void;
  onSendMessage: (text: string, attachments: Attachment[]) => void;
  isRunning: boolean;
  isPlainLlmChat: boolean;
  onStopRun?: () => void;
  /** D9: resume after Stop / fuse. */
  onContinueRun?: () => void;
  awaitingContinue?: boolean;
  runStats?: {
    tool_steps?: number;
    max_steps?: number;
    session_tokens?: number;
    fuse_triggered?: boolean;
  };
  sessionTokens?: number;
  pendingMessages?: PendingChatMessage[];
  onRemovePendingMessage?: (id: string) => void;
  selectedWorkflowId?: string | null;
  selectedWorkflowName?: string;
  onClearSelectedWorkflow?: () => void;
  isMultiAgent?: boolean;
  workspaceFiles?: FileTreeNode[];
  sessions?: SessionRecord[];
  skills?: ScannedSkill[];
  permissionMode: PermissionMode;
  onPermissionModeChange: (mode: PermissionMode) => void;
  shellSessionStatus?: string;
  shellPoolBlockerRunIds?: string[];
  shellPoolBlockers?: ShellPoolBlocker[];
  shellPoolQueuePosition?: number;
  shellPoolQueueDepth?: number;
  currentRunId?: string;
  /** D30 — live status for session board badges. */
  clutchStatus?: string;
  /** D30 — click a board row to switch sessions. */
  onSelectSession?: (session: SessionRecord) => void;
  resolveAgentLogo?: (agentName: string) => string | undefined;
  onDismissHybridNotice?: () => void;
  isFlowRefining?: boolean;
  workflowAgents?: Array<{ nodeId: string; agentName: string; label?: string }>;
  mentionableAgents?: Array<{ id: string; name: string; logo?: string }>;
  selectedMentionAgentId?: string | null;
  onMentionAgentChange?: (agentId: string | null) => void;
  /** D40 — Hub MCP bindings for Clutch Agent Chat badge. */
  mcpServerIds?: string[];
  showMcpBindingBadge?: boolean;
  onOpenMcpBind?: () => void;
  /** D18 — run a chat slash command (/plan /compact /todos /help). */
  onSlashCommand?: (id: SlashCommandId) => void | Promise<void>;
  /** D18 — brief feedback after a slash command. */
  slashNotice?: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

function fileIcon(kind: Attachment['kind']): string {
  if (kind === 'image') return 'image';
  if (kind === 'folder') return 'folder';
  return 'description';
}

function resolveSessionTitle(runId: string, sessions: SessionRecord[]): string {
  const hit = sessions.find((item) => item.run_id === runId);
  const title = hit?.title?.trim();
  if (title) return title;
  return runId.length > 12 ? `${runId.slice(0, 8)}…` : runId;
}

function hybridRejectionNotice(status: string | undefined, lang: 'en' | 'zh'): string | null {
  if (!status?.startsWith('rejected_')) return null;
  const code = status.slice('rejected_'.length);
  // Superseded by pending-message queue (HRT-08).
  if (code === 'run_in_progress') return null;
  const messages: Record<string, { en: string; zh: string }> = {
    session_busy: {
      en: 'Hybrid shell is busy for this chat. Wait or press Stop.',
      zh: '此会话 Hybrid shell 忙碌中。请等待或点击 Stop。',
    },
    pool_full: {
      en: 'All Hybrid shell sessions are busy. Try again when another chat finishes.',
      zh: '所有 Hybrid shell 会话均在忙碌。请待其他会话完成后再试。',
    },
  };
  const entry = messages[code];
  if (!entry) return null;
  return lang === 'zh' ? entry.zh : entry.en;
}

function flattenFileTree(nodes: FileTreeNode[], prefix = ''): string[] {
  const paths: string[] = [];
  for (const node of nodes) {
    const p = prefix ? `${prefix}/${node.name}` : node.name;
    paths.push(p);
    if (node.children) paths.push(...flattenFileTree(node.children, p));
  }
  return paths;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function AttachmentChip({
  att,
  onRemove,
}: {
  att: Attachment;
  onRemove: (id: string) => void;
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5 pl-1.5 pr-1 py-0.5 bg-surface-container border border-outline-variant/40 rounded-lg text-[11px] font-medium text-on-surface max-w-[160px] flex-shrink-0"
    >
      {att.kind === 'image' && att.dataUrl ? (
        <img
          src={att.dataUrl}
          alt={att.name}
          className="w-[22px] h-[22px] rounded object-cover flex-shrink-0 border border-outline-variant/30"
        />
      ) : (
        <LegacyIcon name={fileIcon(att.kind)} className="text-[15px] text-on-surface-variant flex-shrink-0" />
      )}
      <span className="truncate" title={att.name}>{att.name}</span>
      <button
        type="button"
        onClick={() => onRemove(att.id)}
        className={`${BTN_ICON_SM} ml-0.5 flex-shrink-0`}
        aria-label={`Remove ${att.name}`}
      >
        <LegacyIcon name="close" className="text-[13px]" />
      </button>
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

export const ChatInputBar: React.FC<ChatInputBarProps> = ({
  inputValue,
  setInputValue,
  onSendMessage,
  isRunning,
  isPlainLlmChat,
  onStopRun,
  onContinueRun,
  awaitingContinue = false,
  runStats,
  sessionTokens,
  pendingMessages = [],
  onRemovePendingMessage,
  selectedWorkflowId,
  selectedWorkflowName,
  onClearSelectedWorkflow,
  isMultiAgent,
  workspaceFiles = [],
  sessions = [],
  skills = [],
  permissionMode,
  onPermissionModeChange,
  shellSessionStatus,
  shellPoolBlockerRunIds = [],
  shellPoolBlockers = [],
  shellPoolQueuePosition = 0,
  shellPoolQueueDepth = 0,
  currentRunId = '',
  clutchStatus = 'idle',
  onSelectSession,
  resolveAgentLogo,
  onDismissHybridNotice,
  isFlowRefining = false,
  workflowAgents = [],
  mentionableAgents = [],
  selectedMentionAgentId = null,
  onMentionAgentChange,
  mcpServerIds,
  showMcpBindingBadge = false,
  onOpenMcpBind,
  onSlashCommand,
  slashNotice = null,
}) => {
  const { t, language } = useLanguage();
  const [dismissedNoticeKey, setDismissedNoticeKey] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const compositionActiveRef = useRef(false);

  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Menus
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [permissionMenuOpen, setPermissionMenuOpen] = useState(false);

  // Popovers
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [sessionPickerOpen, setSessionPickerOpen] = useState(false);
  const [agentPickerOpen, setAgentPickerOpen] = useState(false);
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);
  const [usageDashboardOpen, setUsageDashboardOpen] = useState(false);
  const [sessionBoardOpen, setSessionBoardOpen] = useState(false);

  const [skillFilter, setSkillFilter] = useState('');
  const [sessionFilter, setSessionFilter] = useState('');
  const [agentFilter, setAgentFilter] = useState('');
  const [fileFilter, setFileFilter] = useState('');

  // Close all menus on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAttachMenuOpen(false);
        setPermissionMenuOpen(false);
        setSkillPickerOpen(false);
        setSessionPickerOpen(false);
        setAgentPickerOpen(false);
        setFileBrowserOpen(false);
        setUsageDashboardOpen(false);
        setSessionBoardOpen(false);
      }
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`;
  }, [inputValue]);

  // ── Attachment helpers ──────────────────────────────────────────────────────

  const addImageFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      setAttachments((prev) => [
        ...prev,
        {
          id: uid(),
          kind: 'image',
          name: file.name,
          dataUrl: reader.result as string,
          mimeType: file.type,
        },
      ]);
    };
    reader.readAsDataURL(file);
  }, []);

  const addFilePath = useCallback((path: string, isFolder = false) => {
    const name = path.split('/').pop() || path;
    setAttachments((prev) => [
      ...prev,
      { id: uid(), kind: isFolder ? 'folder' : 'file', name, path },
    ]);
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  // ── Paste handler ───────────────────────────────────────────────────────────

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const { files } = e.clipboardData;
      if (!files || files.length === 0) return;
      let hasImage = false;
      for (const file of Array.from(files)) {
        if (file.type.startsWith('image/')) {
          e.preventDefault();
          addImageFile(file);
          hasImage = true;
        }
      }
      if (hasImage) return; // let text paste fall through normally
    },
    [addImageFile],
  );

  // ── Drag & Drop handler ─────────────────────────────────────────────────────

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    if (!containerRef.current?.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      // Files dropped from OS
      if (e.dataTransfer.files.length > 0) {
        for (const file of Array.from(e.dataTransfer.files)) {
          if (file.type.startsWith('image/')) {
            addImageFile(file);
          } else {
            addFilePath(file.name);
          }
        }
        return;
      }

      // Path dropped from right panel file tree (text/plain = path string)
      const textData = e.dataTransfer.getData('text/plain');
      if (textData) {
        const isFolder = !textData.includes('.');
        addFilePath(textData, isFolder);
      }
    },
    [addImageFile, addFilePath],
  );

  // ── Local file picker ───────────────────────────────────────────────────────

  const handleLocalFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!e.target.files) return;
      for (const file of Array.from(e.target.files)) {
        if (file.type.startsWith('image/')) {
          addImageFile(file);
        } else {
          addFilePath(file.name);
        }
      }
      e.target.value = '';
    },
    [addImageFile, addFilePath],
  );

  // ── Send ────────────────────────────────────────────────────────────────────

  const runSlashCommand = useCallback(
    (cmd: SlashCommand) => {
      setSkillPickerOpen(false);
      setInputValue('');
      void onSlashCommand?.(cmd.id);
      textareaRef.current?.focus();
    },
    [onSlashCommand, setInputValue],
  );

  const handleSend = useCallback(() => {
    if (!inputValue.trim() && attachments.length === 0) return;
    const slash = matchExactSlashCommand(inputValue);
    if (slash && onSlashCommand) {
      runSlashCommand(slash);
      return;
    }
    onSendMessage(inputValue, attachments);
    setAttachments([]);
    setInputValue('');
  }, [inputValue, attachments, onSendMessage, setInputValue, onSlashCommand, runSlashCommand]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const val = e.target.value;
      setInputValue(val);

      // Detect slash trigger for skills
      const lastSlash = val.lastIndexOf('/');
      if (lastSlash !== -1 && (lastSlash === 0 || val[lastSlash - 1] === ' ' || val[lastSlash - 1] === '\n')) {
        const fragment = val.slice(lastSlash + 1);
        if (!fragment.includes(' ')) {
          setSkillFilter(fragment);
          setSkillPickerOpen(true);
          setSessionPickerOpen(false);
          return;
        }
      }
      setSkillPickerOpen(false);

      // Detect @ trigger for agent mentions
      const lastAt = val.lastIndexOf('@');
      if (
        lastAt !== -1
        && (lastAt === 0 || val[lastAt - 1] === ' ' || val[lastAt - 1] === '\n')
      ) {
        const fragment = val.slice(lastAt + 1);
        if (!fragment.includes(' ')) {
          setAgentFilter(fragment);
          setAgentPickerOpen(true);
          setSessionPickerOpen(false);
          setSkillPickerOpen(false);
          return;
        }
      }
      setAgentPickerOpen(false);

      // Detect hash trigger for sessions
      const lastHash = val.lastIndexOf('#');
      if (lastHash !== -1 && (lastHash === 0 || val[lastHash - 1] === ' ' || val[lastHash - 1] === '\n')) {
        const fragment = val.slice(lastHash + 1);
        if (!fragment.includes(' ')) {
          setSessionFilter(fragment);
          setSessionPickerOpen(true);
          return;
        }
      }
      setSessionPickerOpen(false);
    },
    [setInputValue],
  );

  const insertMentionAgent = useCallback(
    (agentName: string) => {
      const lastAt = inputValue.lastIndexOf('@');
      const before = lastAt >= 0 ? inputValue.slice(0, lastAt) : inputValue;
      setInputValue(`${before}@${agentName} `);
      setAgentPickerOpen(false);
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const insertWorkflowAgent = useCallback(
    (agentName: string) => {
      insertMentionAgent(agentName);
    },
    [insertMentionAgent],
  );

  // ── Skill / Session insert ──────────────────────────────────────────────────

  const insertSkill = useCallback(
    (skill: ScannedSkill) => {
      const lastSlash = inputValue.lastIndexOf('/');
      const before = lastSlash >= 0 ? inputValue.slice(0, lastSlash) : inputValue;
      setInputValue(`${before}/skill:${skill.key} `);
      setSkillPickerOpen(false);
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const insertSession = useCallback(
    (session: SessionRecord) => {
      const lastHash = inputValue.lastIndexOf('#');
      const before = lastHash >= 0 ? inputValue.slice(0, lastHash) : inputValue;
      const label = session.title || session.run_id;
      setInputValue(`${before}#${label} `);
      setSessionPickerOpen(false);
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const insertProjectFile = useCallback(
    (path: string) => {
      addFilePath(path);
      setFileBrowserOpen(false);
      textareaRef.current?.focus();
    },
    [addFilePath],
  );

  // ── Derived ─────────────────────────────────────────────────────────────────

  const filteredSlashCommands = useMemo(
    () => filterSlashCommands(skillFilter),
    [skillFilter],
  );

  const filteredSkills = skills.filter(
    (s) =>
      !skillFilter ||
      s.label.toLowerCase().includes(skillFilter.toLowerCase()) ||
      s.key.toLowerCase().includes(skillFilter.toLowerCase()),
  );
  const filteredSessions = sessions.filter(
    (s) =>
      !sessionFilter ||
      (s.title || '').toLowerCase().includes(sessionFilter.toLowerCase()) ||
      s.run_id.toLowerCase().includes(sessionFilter.toLowerCase()),
  );
  const filteredWorkflowAgents = workflowAgents.filter((step) => {
    const haystack = `${step.agentName} ${step.label ?? ''}`.toLowerCase();
    return !agentFilter || haystack.includes(agentFilter.toLowerCase());
  });
  const showWorkflowAgentPicker = isFlowRefining && workflowAgents.length > 0;

  useEffect(() => {
    if (!onMentionAgentChange || showWorkflowAgentPicker) return;
    const hit = parseInputAgentMention(inputValue, mentionableAgents);
    onMentionAgentChange(hit?.agentId ?? null);
  }, [inputValue, mentionableAgents, onMentionAgentChange, showWorkflowAgentPicker]);
  const filteredMentionableAgents = mentionableAgents.filter((agent) => {
    const haystack = agent.name.toLowerCase();
    return !agentFilter || haystack.includes(agentFilter.toLowerCase());
  });
  const activeAgentPickerItems = showWorkflowAgentPicker
    ? filteredWorkflowAgents
    : filteredMentionableAgents;
  const allFilePaths = flattenFileTree(workspaceFiles);
  const filteredFiles = allFilePaths.filter(
    (p) => !fileFilter || p.toLowerCase().includes(fileFilter.toLowerCase()),
  );

  const canSend = inputValue.trim().length > 0 || attachments.length > 0;
  const showPlainChatStop = isRunning && isPlainLlmChat;
  const showPlainChatContinue =
    !isRunning && isPlainLlmChat && Boolean(awaitingContinue) && Boolean(onContinueRun);
  const stepsUsed = runStats?.tool_steps ?? 0;
  const stepsMax = runStats?.max_steps ?? 24;
  const tokensShown = runStats?.session_tokens ?? sessionTokens ?? 0;
  const showRunStats =
    isPlainLlmChat && (isRunning || awaitingContinue || stepsUsed > 0 || tokensShown > 0);
  const currentPermission = PERMISSION_MODES.find((m) => m.id === permissionMode) ?? PERMISSION_MODES[0];
  const hybridNotice = hybridRejectionNotice(shellSessionStatus, language === 'zh' ? 'zh' : 'en');
  const showHybridNotice =
    hybridNotice && dismissedNoticeKey !== (shellSessionStatus ?? '');
  const isPoolQueued = shellSessionStatus === 'queued_pool';
  const poolBlockers = useMemo((): ShellPoolBlocker[] => {
    const fromBackend = shellPoolBlockers.filter(
      (item) => item.run_id.trim().length > 0 && item.run_id !== currentRunId,
    );
    if (fromBackend.length > 0) return fromBackend;
    return shellPoolBlockerRunIds
      .filter((runId) => runId.trim().length > 0 && runId !== currentRunId)
      .map((runId) => ({
        run_id: runId,
        title: resolveSessionTitle(runId, sessions),
        agent_name: '',
      }));
  }, [shellPoolBlockers, shellPoolBlockerRunIds, currentRunId, sessions]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Escape') {
        setSkillPickerOpen(false);
        setSessionPickerOpen(false);
        setAgentPickerOpen(false);
        setFileBrowserOpen(false);
        return;
      }

      const isComposing = compositionActiveRef.current || e.nativeEvent.isComposing;
      if (
        skillPickerOpen &&
        shouldSubmitChatOnEnter(e.nativeEvent, isComposing)
      ) {
        if (filteredSlashCommands.length > 0) {
          e.preventDefault();
          runSlashCommand(filteredSlashCommands[0]);
          return;
        }
        if (filteredSkills.length > 0) {
          e.preventDefault();
          insertSkill(filteredSkills[0]);
          return;
        }
      }
      if (
        sessionPickerOpen &&
        filteredSessions.length > 0 &&
        shouldSubmitChatOnEnter(e.nativeEvent, isComposing)
      ) {
        e.preventDefault();
        insertSession(filteredSessions[0]);
        return;
      }

      if (
        agentPickerOpen
        && activeAgentPickerItems.length > 0
        && shouldSubmitChatOnEnter(e.nativeEvent, isComposing)
      ) {
        e.preventDefault();
        if (showWorkflowAgentPicker) {
          insertWorkflowAgent(filteredWorkflowAgents[0].agentName);
        } else {
          insertMentionAgent(filteredMentionableAgents[0].name);
        }
        return;
      }

      if (!shouldSubmitChatOnEnter(e.nativeEvent, isComposing)) return;

      e.preventDefault();
      if (canSend) {
        handleSend();
      }
    },
    [
      canSend,
      filteredSessions,
      filteredSkills,
      filteredSlashCommands,
      handleSend,
      insertSession,
      insertSkill,
      runSlashCommand,
      sessionPickerOpen,
      agentPickerOpen,
      filteredMentionableAgents,
      filteredWorkflowAgents,
      insertMentionAgent,
      insertWorkflowAgent,
      showWorkflowAgentPicker,
      skillPickerOpen,
    ],
  );

  useEffect(() => {
    setDismissedNoticeKey(null);
  }, [shellSessionStatus]);

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div
      ref={containerRef}
      className={`relative w-full bg-white border shadow-xl rounded-xl transition-all ${
        isDragging
          ? 'border-primary/60 ring-2 ring-primary/20'
          : 'border-outline-variant focus-within:ring-2 focus-within:ring-primary/10'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {showHybridNotice ? (
        <div className="flex items-start gap-2 px-3 py-2 text-[11px] leading-snug text-amber-900 bg-amber-50 border-b border-amber-200/80 rounded-t-xl">
          <span className="flex-1">{hybridNotice}</span>
          <button
            type="button"
            onClick={() => {
              setDismissedNoticeKey(shellSessionStatus ?? '');
              onDismissHybridNotice?.();
            }}
            className={`${BTN_ICON_SM} flex-shrink-0 text-amber-800/70 hover:text-amber-950 hover:bg-amber-100/80`}
            aria-label={language === 'zh' ? '关闭提示' : 'Dismiss notice'}
          >
            <LegacyIcon name="close" className="text-[14px]" />
          </button>
        </div>
      ) : null}
      {isPoolQueued ? (
        <div className="px-3 pt-3 pb-2 border-b border-outline-variant/40">
          <div className="flex items-center gap-1.5 mb-2">
            <Loader2 className="w-3.5 h-3.5 text-primary animate-spin flex-shrink-0" />
            <span className="text-[11px] font-semibold text-on-surface-variant">
              {language === 'zh' ? 'Hybrid shell 排队中' : 'Waiting for Hybrid shell'}
            </span>
          </div>
          <div className="space-y-1.5">
            {poolBlockers.length > 0 ? (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant/70 mb-1.5 px-0.5">
                  {language === 'zh' ? '等待以下会话释放 shell' : 'Waiting for these sessions'}
                </p>
                <ul className="space-y-1.5 max-h-24 overflow-y-auto">
                  {poolBlockers.map((blocker) => {
                    const title =
                      blocker.title?.trim()
                      || resolveSessionTitle(blocker.run_id, sessions);
                    const agentName = blocker.agent_name?.trim() ?? '';
                    const logoSrc = agentName ? resolveAgentLogo?.(agentName) : undefined;
                    return (
                      <li
                        key={blocker.run_id}
                        className="flex items-center gap-2 rounded-lg border border-outline-variant/50 bg-surface-container-low/60 px-2.5 py-1.5 min-w-0"
                      >
                        <AgentChatAvatar
                          src={logoSrc}
                          alt={agentName || title}
                          className="w-6 h-6"
                        />
                        <div className="flex-1 min-w-0">
                          <span className="block text-[12px] text-on-surface truncate font-medium" title={title}>
                            {title}
                          </span>
                          {agentName ? (
                            <span className="block text-[10px] text-on-surface-variant/70 truncate" title={agentName}>
                              {agentName}
                            </span>
                          ) : null}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : (
              <p className="text-[11px] text-on-surface-variant px-0.5">
                {language === 'zh'
                  ? 'Shell 槽位已满，等待其他会话释放…'
                  : 'Shell pool is full; waiting for a slot…'}
              </p>
            )}
            {shellPoolQueuePosition > 0 ? (
              <p className="text-[11px] text-on-surface-variant px-0.5">
                {language === 'zh'
                  ? `全局队列第 ${shellPoolQueuePosition} 位${
                      shellPoolQueueDepth > 0 ? `（共 ${shellPoolQueueDepth} 条）` : ''
                    }`
                  : `Queue position ${shellPoolQueuePosition}${
                      shellPoolQueueDepth > 0 ? ` of ${shellPoolQueueDepth}` : ''
                    } globally`}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
      {isPlainLlmChat ? (
        <div
          className="flex items-center gap-1 px-3 pt-2"
          data-testid="chat-mode-presets"
        >
          {CHAT_MODE_PRESETS.map((preset) => {
            const active = permissionMode === preset.id;
            return (
              <button
                key={preset.id}
                type="button"
                data-testid={`chat-mode-${preset.id}`}
                title={preset.label}
                onClick={() => onPermissionModeChange(preset.id)}
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold transition-colors ${
                  active
                    ? preset.id === 'explore'
                      ? 'bg-violet-100 text-violet-700'
                      : preset.id === 'plan'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-emerald-100 text-emerald-700'
                    : 'bg-surface-container-low text-on-surface-variant/70 hover:text-on-surface'
                }`}
              >
                {preset.shortLabel}
              </button>
            );
          })}
        </div>
      ) : null}
      {showMcpBindingBadge || showRunStats || (sessions.length > 0 && isPlainLlmChat) ? (
        <div
          className="relative flex items-center justify-between gap-2 px-3 pt-2 pb-1 text-[10px] text-on-surface-variant/70 border-b border-outline-variant/30"
        >
          <SessionOverviewBoard
            open={sessionBoardOpen && isPlainLlmChat}
            onClose={() => setSessionBoardOpen(false)}
            sessions={sessions}
            currentRunId={currentRunId}
            clutchStatus={clutchStatus}
            language={language === 'zh' ? 'zh' : 'en'}
            onSelectSession={onSelectSession}
          />
          <UsageDashboard
            open={usageDashboardOpen && isPlainLlmChat}
            onClose={() => setUsageDashboardOpen(false)}
            currentRunId={currentRunId}
            sessions={sessions}
            runStats={runStats}
            sessionTokens={sessionTokens}
            language={language === 'zh' ? 'zh' : 'en'}
          />
          <div className="flex items-center gap-2 min-w-0">
            {isPlainLlmChat && sessions.length > 0 ? (
              <button
                type="button"
                data-testid="session-overview-toggle"
                title={language === 'zh' ? '会话总览' : 'Session overview'}
                onClick={() => {
                  setUsageDashboardOpen(false);
                  setSessionBoardOpen((open) => !open);
                }}
                className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 hover:bg-surface-container-low hover:text-on-surface transition-colors"
              >
                <LegacyIcon name="view_list" className="text-[13px]" />
                <span>{language === 'zh' ? '会话' : 'Sessions'}</span>
              </button>
            ) : null}
            {showMcpBindingBadge ? (
              <McpBindingBadge
                mcpServerIds={mcpServerIds}
                visible
                onOpenBind={onOpenMcpBind}
              />
            ) : null}
            {showRunStats ? (
              <button
                type="button"
                data-testid="chat-run-stats"
                title={language === 'zh' ? '打开用量看板' : 'Open usage dashboard'}
                onClick={() => {
                  setSessionBoardOpen(false);
                  setUsageDashboardOpen((open) => !open);
                }}
                className="font-mono truncate text-left hover:text-on-surface transition-colors"
              >
                {language === 'zh' ? '步骤' : 'Steps'} {stepsUsed}/{stepsMax}
                {' · '}
                ~{tokensShown.toLocaleString()} {language === 'zh' ? 'token' : 'tok'}
              </button>
            ) : null}
          </div>
          {showRunStats && runStats?.fuse_triggered ? (
            <span className="text-rose-600 font-semibold not-italic shrink-0">
              {language === 'zh' ? '已熔断' : 'Loop fuse'}
            </span>
          ) : null}
        </div>
      ) : null}
      {pendingMessages.length > 0 ? (
        <div className="px-3 pt-3 pb-2 border-b border-outline-variant/40">
          <div className="flex items-center gap-1.5 mb-2">
            <span className="text-[11px] font-semibold text-on-surface-variant">
              {language === 'zh' ? '待发送消息' : 'Pending messages'}
            </span>
            <LegacyIcon name="info" className="text-[13px] text-on-surface-variant/50" />
          </div>
          <div className="space-y-1.5 max-h-24 overflow-y-auto">
            {pendingMessages.map((item, index) => (
              <div
                key={item.id}
                data-testid={`pending-message-${index + 1}`}
                className="flex items-center gap-2 rounded-lg border border-outline-variant/50 bg-surface-container-low/60 px-2.5 py-1.5"
              >
                <span
                  className="shrink-0 rounded-md bg-surface-container-high/80 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-on-surface-variant"
                  data-testid={`pending-queue-position-${index + 1}`}
                >
                  {queuePositionLabel(index, language)}
                </span>
                <span className="flex-1 text-[12px] text-on-surface truncate" title={item.text}>
                  {item.text}
                </span>
                <button
                  type="button"
                  onClick={() => onRemovePendingMessage?.(item.id)}
                  className={`${BTN_ICON_SM} text-on-surface-variant/60 hover:text-red-600 hover:bg-red-50`}
                  aria-label={language === 'zh' ? '移出队列' : 'Remove from queue'}
                >
                  <LegacyIcon name="delete" className="text-[15px]" />
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {/* Hidden native file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleLocalFileChange}
      />

      {/* Workflow chip — Multi-Agent only */}
      {isMultiAgent && selectedWorkflowId ? (
        <div className="flex flex-wrap gap-1.5 px-3 pt-2 pb-1">
          <span className="inline-flex items-center gap-1.5 pl-1.5 pr-1 py-0.5 text-[11px] font-bold text-primary bg-primary/5 border border-primary/20 rounded-lg max-w-[220px]">
            <LegacyIcon name="fork_right" className="text-[14px] flex-shrink-0" />
            <span className="truncate" title={selectedWorkflowName || selectedWorkflowId}>
              {selectedWorkflowName || selectedWorkflowId}
            </span>
            <button
              type="button"
              onClick={onClearSelectedWorkflow}
              className={`${BTN_ICON_SM} ml-0.5 text-primary/60 hover:text-primary flex-shrink-0`}
              aria-label={t('Remove workflow')}
            >
              <LegacyIcon name="close" className="text-[13px]" />
            </button>
          </span>
        </div>
      ) : null}

      {/* Attachment chips */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-3 pt-2 pb-0.5">
          {attachments.map((att) => (
            <AttachmentChip key={att.id} att={att} onRemove={removeAttachment} />
          ))}
        </div>
      )}

      {/* Drop overlay hint */}
      {isDragging && (
        <div className="px-3 pt-2 pb-0">
          <div className="flex items-center gap-2 py-2 px-3 bg-primary/5 border border-primary/20 rounded-lg">
            <LegacyIcon name="upload_file" className="text-primary text-[18px]" />
            <span className="text-xs text-primary font-medium">{t('Drop to attach')}</span>
          </div>
        </div>
      )}

      {/* Text area row */}
      <div className="flex items-center gap-1.5 px-2 py-1.5">
        {/* + Attach button */}
        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => {
              setAttachMenuOpen((v) => !v);
              setPermissionMenuOpen(false);
            }}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-on-surface-variant/60 hover:text-on-surface hover:bg-surface-container transition-colors"
            title={t('Attach')}
          >
            <LegacyIcon name="add" className="text-[19px]" />
          </button>

          {attachMenuOpen && (
            <div className="absolute bottom-full left-0 mb-2 w-52 bg-white border border-outline-variant rounded-xl shadow-xl py-1.5 z-50 animate-in fade-in slide-in-from-bottom-1 duration-150">
              {/* Add attachment (local) */}
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  fileInputRef.current?.click();
                }}
              >
                <LegacyIcon name="attach_file" className="text-[17px] text-on-surface-variant" />
                Add attachment
              </button>

              {/* @mention project file */}
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  setFileBrowserOpen(true);
                  setFileFilter('');
                }}
              >
                <LegacyIcon name="alternate_email" className="text-[17px] text-on-surface-variant" />
                Insert @ mention
              </button>

              {/* #session */}
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  setSessionPickerOpen(true);
                  setSessionFilter('');
                }}
              >
                <LegacyIcon name="chat_bubble" className="text-[17px] text-on-surface-variant" />
                Insert # session
              </button>

              {/* /command */}
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  setSkillPickerOpen(true);
                  setSkillFilter('');
                }}
              >
                <LegacyIcon name="terminal" className="text-[17px] text-on-surface-variant" />
                Insert / command
              </button>
            </div>
          )}
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          data-testid="chat-input"
          value={inputValue}
          onChange={handleInputChange}
          onCompositionStart={() => {
            compositionActiveRef.current = true;
          }}
          onCompositionEnd={() => {
            compositionActiveRef.current = false;
          }}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          className="w-full border-none focus:ring-0 text-[13px] text-on-surface bg-transparent pt-[6px] pb-[2px] resize-none min-h-8 max-h-[140px] placeholder:text-on-surface-variant/60 outline-none leading-5"
          placeholder={
            isFlowRefining
              ? t('@Agent your feedback (Hybrid) — auto-continues downstream; Stop to pause')
              : isMultiAgent && selectedWorkflowId
              ? t('Describe what you want this workflow to do...')
              : isMultiAgent
              ? t('Ask @Agent or describe your workflow...')
              : t('Ask your AI Agent anything...')
          }
          rows={1}
        />

        {/* Right controls */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {/* Permission mode button */}
          <div className="relative">
            <button
              type="button"
              title={`Permission: ${currentPermission.label}`}
              onClick={() => {
                setPermissionMenuOpen((v) => !v);
                setAttachMenuOpen(false);
              }}
              className={`w-8 h-8 flex items-center justify-center rounded-lg transition-colors ${
                permissionMode === 'full'
                  ? 'text-amber-500 hover:bg-amber-50'
                  : permissionMode === 'explore'
                  ? 'text-violet-500 hover:bg-violet-50'
                  : permissionMode === 'plan'
                  ? 'text-blue-500 hover:bg-blue-50'
                  : permissionMode === 'auto_edit'
                  ? 'text-emerald-500 hover:bg-emerald-50'
                  : 'text-on-surface-variant/60 hover:text-on-surface hover:bg-surface-container'
              }`}
            >
              <LegacyIcon name={currentPermission.icon} className="text-[18px]" />
            </button>

            {permissionMenuOpen && (
              <div className="absolute bottom-full right-0 mb-2 w-60 bg-white border border-outline-variant rounded-xl shadow-xl py-1.5 z-50 animate-in fade-in slide-in-from-bottom-1 duration-150">
                {PERMISSION_MODES.map((mode) => (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => {
                      onPermissionModeChange(mode.id);
                      setPermissionMenuOpen(false);
                    }}
                    className="w-full flex items-start gap-3 px-3 py-2.5 hover:bg-surface-container-low transition-colors text-left group"
                  >
                    <LegacyIcon
                      name={mode.icon}
                      className={`text-[18px] mt-0.5 flex-shrink-0 ${
                        mode.id === permissionMode
                          ? mode.id === 'full'
                            ? 'text-amber-500'
                            : mode.id === 'explore'
                            ? 'text-violet-500'
                            : mode.id === 'plan'
                            ? 'text-blue-500'
                            : mode.id === 'auto_edit'
                            ? 'text-emerald-500'
                            : 'text-on-surface-variant'
                          : 'text-on-surface-variant/50'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-[12px] font-semibold text-on-surface">{mode.label}</span>
                        {mode.id === permissionMode && (
                          <LegacyIcon name="check" className="text-[14px] text-primary" />
                        )}
                      </div>
                      <span className="text-[10.5px] text-on-surface-variant/70">{mode.description}</span>
                    </div>
                  </button>
                ))}
                <div className="border-t border-outline-variant/60 my-1 mx-3" />
                <button
                  type="button"
                  data-testid="clear-approvals"
                  className="w-full px-3 py-2 text-left text-[11px] font-semibold text-on-surface hover:bg-surface-container-low transition-colors"
                  onClick={() => {
                    setPermissionMenuOpen(false);
                    void clutchStore.send({ action: 'clear_approvals' });
                  }}
                >
                  {t('Clear remembered approvals')}
                </button>
                <div className="px-3 py-1.5 text-[9.5px] leading-normal text-on-surface-variant/60">
                  {t('Note: These settings only apply to the built-in Clutch Agent and MCP tools, and do not affect CLI Agents (such as Claude Code).')}
                </div>
              </div>
            )}
          </div>

          {/* Stop / Continue (D9) + Send */}
          {showPlainChatStop ? (
            <button
              type="button"
              data-testid="chat-stop"
              onClick={onStopRun}
              className="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-900 text-white hover:bg-black transition-all"
              title={t('Stop')}
              aria-label={t('Stop')}
            >
              <LegacyIcon name="stop" className="text-[17px]" />
            </button>
          ) : null}
          {showPlainChatContinue ? (
            <button
              type="button"
              data-testid="chat-continue"
              onClick={onContinueRun}
              className="h-8 px-2.5 flex items-center justify-center rounded-full bg-neutral-900 text-white hover:bg-black transition-all text-[11px] font-semibold"
              title={t('Continue')}
              aria-label={t('Continue')}
            >
              {t('Continue')}
            </button>
          ) : null}
          <button
            type="button"
            data-testid="chat-send"
            onClick={handleSend}
            disabled={!canSend}
            className={`w-8 h-8 flex items-center justify-center rounded-full transition-all ${
              canSend
                ? 'bg-primary text-white hover:opacity-90'
                : 'bg-surface-container text-on-surface-variant/40 cursor-not-allowed'
            }`}
          >
            <LegacyIcon name="arrow_upward" className="text-[17px]" />
          </button>
        </div>
      </div>

      {/* ── Agent picker (@) ── */}
      {agentPickerOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-150">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="smart_toy" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">
                {showWorkflowAgentPicker ? t('Workflow agents') : t('AI Agents')}
              </span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {showWorkflowAgentPicker ? (
              filteredWorkflowAgents.length === 0 ? (
                <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">{t('No agents in this workflow')}</p>
              ) : (
                filteredWorkflowAgents.map((step) => (
                  <button
                    key={step.nodeId}
                    type="button"
                    onClick={() => insertWorkflowAgent(step.agentName)}
                    className="w-full flex flex-col px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                  >
                    <span className="text-[12px] font-semibold text-on-surface">@{step.agentName}</span>
                    {step.label && step.label !== step.agentName ? (
                      <span className="text-[10.5px] text-on-surface-variant/60 truncate">{step.label}</span>
                    ) : null}
                  </button>
                ))
              )
            ) : filteredMentionableAgents.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">{t('No matching agents')}</p>
            ) : (
              filteredMentionableAgents.map((agent) => (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => insertMentionAgent(agent.name)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                >
                  {agent.logo ? (
                    <img src={agent.logo} alt="" className="w-5 h-5 rounded object-contain shrink-0" />
                  ) : (
                    <span className="w-5 h-5 rounded bg-surface-container-low shrink-0" />
                  )}
                  <span className="flex-1 min-w-0 flex items-center justify-between gap-2">
                    <span className="text-[12px] font-semibold text-on-surface truncate">@{agent.name}</span>
                    {agent.id === selectedMentionAgentId ? (
                      <LegacyIcon name="check" className="text-[14px] text-primary shrink-0" />
                    ) : null}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Slash commands + skill picker (D18) ── */}
      {skillPickerOpen && (
        <div
          className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-150"
          data-testid="slash-command-picker"
          style={{ bottom: '100%', left: 0 }}
        >
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="terminal" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">{t('Skills / Commands')}</span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredSlashCommands.length > 0 && (
              <div className="py-1 border-b border-outline-variant/20">
                {filteredSlashCommands.map((cmd) => (
                  <button
                    key={cmd.id}
                    type="button"
                    data-testid={`slash-cmd-${cmd.id}`}
                    onClick={() => runSlashCommand(cmd)}
                    className="w-full flex flex-col px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                  >
                    <span className="text-[12px] font-semibold text-on-surface">{cmd.label}</span>
                    <span className="text-[10.5px] text-on-surface-variant/60 truncate">{cmd.description}</span>
                  </button>
                ))}
              </div>
            )}
            {filteredSkills.length === 0 && filteredSlashCommands.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">
                {skills.length === 0 ? t('No skills loaded') : t('No matches')}
              </p>
            ) : (
              filteredSkills.map((skill) => (
                <button
                  key={skill.key}
                  type="button"
                  onClick={() => insertSkill(skill)}
                  className="w-full flex flex-col px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                >
                  <span className="text-[12px] font-semibold text-on-surface">{skill.label}</span>
                  {skill.desc && (
                    <span className="text-[10.5px] text-on-surface-variant/60 truncate">{skill.desc}</span>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {slashNotice ? (
        <div
          data-testid="slash-command-notice"
          className="absolute bottom-full left-0 mb-1 px-2.5 py-1.5 rounded-lg bg-surface-container text-[11px] text-on-surface shadow border border-outline-variant/40 max-w-[min(100%,22rem)]"
        >
          {slashNotice}
        </div>
      ) : null}

      {/* ── Session picker popover ── */}
      {sessionPickerOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-150">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="chat_bubble" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">{t('Sessions')}</span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredSessions.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">{t('No sessions yet')}</p>
            ) : (
              filteredSessions.slice(0, 12).map((session) => (
                <button
                  key={session.run_id}
                  type="button"
                  onClick={() => insertSession(session)}
                  className="w-full flex flex-col px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                >
                  <span className="text-[12px] font-semibold text-on-surface truncate">
                    {session.title || session.run_id}
                  </span>
                  <span className="text-[10px] text-on-surface-variant/50">
                    {session.started_at ? new Date(session.started_at).toLocaleDateString() : ''}
                    {session.workflow_id ? ` · ${session.workflow_id}` : ''}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Project file browser popover ── */}
      {fileBrowserOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-150">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2 pb-1">
              <LegacyIcon name="folder_open" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">{t('Project Files')}</span>
            </div>
            <input
              type="text"
              value={fileFilter}
              onChange={(e) => setFileFilter(e.target.value)}
              placeholder={t('Filter files...')}
              className="w-full text-[11px] px-2 py-1.5 bg-surface-container rounded-lg border-none outline-none text-on-surface placeholder:text-on-surface-variant/50"
              autoFocus
            />
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredFiles.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">
                {allFilePaths.length === 0 ? t('No workspace files loaded') : t('No matches')}
              </p>
            ) : (
              filteredFiles.slice(0, 30).map((path) => (
                <button
                  key={path}
                  type="button"
                  onClick={() => insertProjectFile(path)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-surface-container-low transition-colors"
                >
                  <LegacyIcon
                    name={path.endsWith('/') ? 'folder' : 'description'}
                    className="text-[14px] text-on-surface-variant flex-shrink-0"
                  />
                  <span className="text-[11px] text-on-surface truncate" title={path}>{path}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
