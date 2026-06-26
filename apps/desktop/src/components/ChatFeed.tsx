import React, { useRef, useEffect, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { ChatMessage, ClutchRunStatus, HybridExecutionPayload, OutputEvent } from '../types';
import { useLanguage } from './LanguageContext';
import { ChatInputBar, type Attachment } from './ChatInputBar';
import { BTN_DANGER_SM, BTN_PRIMARY, BTN_SECONDARY, BTN_SM, BTN_SUCCESS_SM } from './ui/buttonStyles';
import type { SessionRecord } from '../services/runApi';
import type { ScannedSkill } from '../services/skillsApi';
import type { FileTreeNode } from '../services/workspaceApi';
import type { PermissionMode } from '../services/permissionApi';

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
  onStopRun?: () => void;
  isMultiAgent?: boolean;
  onApprove?: () => void;
  onReject?: () => void;
  onRetryWithInstructions?: (instructions: string) => void;
  workspaceAuthorized?: boolean;
  onPickWorkspace?: () => void;
  onOpenWorkflows?: () => void;
  workspacePickError?: string | null;
  selectedWorkflowId?: string | null;
  selectedWorkflowName?: string;
  onClearSelectedWorkflow?: () => void;
  sessionTitle?: string;
  activeWorkflowId?: string;
  llmModelName?: string;
  activeAgentName?: string;
  engineHint?: string;
  // New props for ChatInputBar
  workspaceFiles?: FileTreeNode[];
  sessions?: SessionRecord[];
  skills?: ScannedSkill[];
  permissionMode?: PermissionMode;
  onPermissionModeChange?: (mode: PermissionMode) => void;
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
  if (key.includes('ollama') || key === 'ollama-cli') return 'Ollama CLI';
  return agentTypeOrLegacy.trim();
}

function replyRuntimeLabel(
  runtimeEngine: string | undefined,
  fallbackModelName: string,
): string {
  return runtimeEngine?.trim() || fallbackModelName || '—';
}

const IMAGE_MARKER_RE = /\[image:\s*(data:image\/[^\]]+)\]\s*/gi;
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

function parseChatContent(text: string): { text: string; images: Array<{ src: string; alt: string }> } {
  const fromMarkers = parseMessageImages(text);
  const fromMarkdown = parseMarkdownImages(fromMarkers.text);
  return {
    text: fromMarkdown.text,
    images: dedupeImages([
      ...fromMarkers.images.map((src) => ({ src, alt: 'Attached screenshot' })),
      ...fromMarkdown.images,
    ]),
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
        <span className="material-symbols-outlined text-[16px]">image</span>
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

function renderMarkdown(text: string): React.ReactNode {
  if (!text) return null;

  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];

  let inBlockquote = false;
  let blockquoteLines: string[] = [];
  let isAlert = false;
  let alertType = ''; // 'IMPORTANT', 'WARNING', 'NOTE', 'TIP'

  const flushBlockquote = (key: number) => {
    if (blockquoteLines.length === 0 && !isAlert) return;

    const content = blockquoteLines.join('\n');
    blockquoteLines = [];
    inBlockquote = false;

    // Inline formatting helper
    const formatInline = (str: string) => {
      return str
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code class="bg-neutral-200/60 dark:bg-neutral-800 text-on-surface px-1 py-0.5 rounded font-mono text-[11px] border border-outline-variant/20 mx-0.5">$1</code>');
    };

    if (isAlert) {
      // Render GitHub-style alert box
      const title = alertType;
      let borderClass = 'border-l-4 border-blue-500';
      let bgClass = 'bg-blue-50/50';
      let textClass = 'text-blue-900';
      let icon = 'info';

      if (alertType === 'IMPORTANT') {
        borderClass = 'border-l-4 border-violet-500';
        bgClass = 'bg-violet-50/40';
        textClass = 'text-violet-900';
        icon = 'label_important';
      } else if (alertType === 'WARNING') {
        borderClass = 'border-l-4 border-amber-500';
        bgClass = 'bg-amber-50/40';
        textClass = 'text-amber-900';
        icon = 'warning';
      } else if (alertType === 'TIP') {
        borderClass = 'border-l-4 border-emerald-500';
        bgClass = 'bg-emerald-50/40';
        textClass = 'text-emerald-900';
        icon = 'lightbulb';
      }

      elements.push(
        <div key={`alert-${key}`} className={`p-3.5 my-3 rounded-r-xl border border-y-outline-variant/20 border-r-outline-variant/20 ${borderClass} ${bgClass} flex items-start gap-2.5`}>
          <span className={`material-symbols-outlined text-[18px] mt-0.5 ${textClass}`}>{icon}</span>
          <div className="flex-1 space-y-1">
            <div className={`text-[11px] font-bold tracking-wide uppercase ${textClass}`}>{title}</div>
            <div className="text-[12.5px] leading-relaxed text-on-surface" dangerouslySetInnerHTML={{ __html: formatInline(content) }} />
          </div>
        </div>
      );
    } else {
      // Standard blockquote
      elements.push(
        <blockquote key={`bq-${key}`} className="pl-4 border-l-4 border-neutral-300 my-2 text-neutral-500 italic text-[12.5px]" dangerouslySetInnerHTML={{ __html: formatInline(content) }} />
      );
    }

    isAlert = false;
    alertType = '';
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Handle blockquote
    if (trimmed.startsWith('>')) {
      let content = line.substring(line.indexOf('>') + 1);
      if (content.startsWith(' ')) {
        content = content.substring(1);
      }

      // Check for alert header: [!IMPORTANT], [!WARNING], [!NOTE], [!TIP]
      const alertMatch = content.match(/^\[!(IMPORTANT|WARNING|NOTE|TIP)\]/i);
      if (alertMatch) {
        isAlert = true;
        alertType = alertMatch[1].toUpperCase();
        inBlockquote = true;
      } else {
        blockquoteLines.push(content);
        inBlockquote = true;
      }
      continue;
    }

    // If we were in blockquote but the current line is not, flush the blockquote
    if (inBlockquote) {
      flushBlockquote(i);
    }

    // Handle markdown images: ![alt](url)
    const imageMatch = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (imageMatch) {
      elements.push(
        <div key={i} className="my-3">
          <ChatBubbleImage src={imageMatch[2]} alt={imageMatch[1] || 'generated image'} />
        </div>
      );
      continue;
    }

    // Handle markdown links on their own line (e.g. "Open image")
    const linkMatch = trimmed.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      elements.push(
        <a
          key={i}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[12px] text-primary font-medium hover:underline my-1"
        >
          {linkMatch[1]}
        </a>
      );
      continue;
    }

    // Handle Headings
    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={i} className="text-base font-extrabold text-neutral-900 border-b border-neutral-200 pb-1.5 mb-3 mt-3">
          {trimmed.substring(2)}
        </h1>
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="text-sm font-bold text-neutral-800 mt-4 mb-1.5">
          {trimmed.substring(3)}
        </h2>
      );
      continue;
    }
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="text-xs font-bold text-neutral-800 mt-3 mb-1">
          {trimmed.substring(4)}
        </h3>
      );
      continue;
    }

    // Handle List Items
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.substring(2);
      const formatInline = (str: string) => {
        return str
          .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-on-surface">$1</strong>')
          .replace(/`([^`]+)`/g, '<code class="bg-neutral-200/60 dark:bg-neutral-800 text-on-surface px-1 py-0.5 rounded font-mono text-[11px] border border-outline-variant/20 mx-0.5">$1</code>');
      };
      elements.push(
        <div key={i} className="flex items-start gap-2 pl-2 my-1 text-on-surface text-[13px]">
          <span className="w-1 h-1 mt-2 rounded bg-neutral-400 flex-shrink-0" />
          <span dangerouslySetInnerHTML={{ __html: formatInline(content) }} />
        </div>
      );
      continue;
    }

    // Handle normal paragraphs
    const formatInline = (str: string) => {
      return str
        .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-on-surface">$1</strong>')
        .replace(/`([^`]+)`/g, '<code class="bg-neutral-200/60 dark:bg-neutral-800 text-on-surface px-1 py-0.5 rounded font-mono text-[11px] border border-outline-variant/20 mx-0.5">$1</code>');
    };

    if (trimmed === '') {
      elements.push(<div key={i} className="h-2" />);
    } else {
      elements.push(
        <p key={i} className="my-1.5 text-on-surface text-[13px] leading-relaxed" dangerouslySetInnerHTML={{ __html: formatInline(line) }} />
      );
    }
  }

  // Final flush in case file ends with blockquote
  if (inBlockquote) {
    flushBlockquote(lines.length);
  }

  return <div className="space-y-1 select-text">{elements}</div>;
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
  onStopRun,
  isMultiAgent = true,
  onApprove,
  onReject,
  onRetryWithInstructions,
  workspaceAuthorized = false,
  onPickWorkspace,
  onOpenWorkflows,
  workspacePickError = null,
  selectedWorkflowId = null,
  selectedWorkflowName = '',
  onClearSelectedWorkflow,
  sessionTitle = '',
  activeWorkflowId = '',
  llmModelName = '',
  activeAgentName = '',
  engineHint = '',
  workspaceFiles = [],
  sessions = [],
  skills = [],
  permissionMode = 'ask',
  onPermissionModeChange,
}) => {
  const { t } = useLanguage();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [hillInstructions, setHillInstructions] = useState('');

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
    onSendMessage(fullText.trim(), attachments);
  };

  const isIdle = clutchStatus === 'idle';
  const isRunning = clutchStatus === 'running';
  const awaitingHuman = clutchStatus === 'awaiting_human';
  const isPlainLlmChat = isPlainLlmSession(selectedWorkflowId, activeWorkflowId);

  const isDefaultNewSessionTitle = !sessionTitle ||
    sessionTitle === 'New session' ||
    sessionTitle === 'New Chat' ||
    sessionTitle === 'New session / 新建会话' ||
    sessionTitle === 'New Chat / 新建会话' ||
    sessionTitle === '新建会话';

  const showEmptyState = isIdle && messages.length === 0 && isDefaultNewSessionTitle;

  const lastUserIndex = messages.findLastIndex((message) => message.agent === 'User');
  const lastAgentIndex = messages.findLastIndex((message) => message.agent !== 'User');
  const showThinking =
    isRunning && lastUserIndex >= 0 && lastUserIndex > lastAgentIndex;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, clutchStatus, showThinking]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isRunning && isPlainLlmChat) return;
      if (inputValue.trim()) {
        onSendMessage(inputValue);
        setInputValue('');
      }
    }
  };

  const handleSendClick = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  const renderAgentLabel = (
    agent: string,
    statusHint?: string,
    runtimeEngine?: string,
  ) => {
    const showPlainLlmLabel = isPlainLlmChat && isPlainLlmReply(agent);

    if (showPlainLlmLabel || (statusHint && isPlainLlmChat)) {
      const agentTitle = activeAgentName || t('Clutch Agent');
      const engineLabel = statusHint
        ? replyRuntimeLabel(engineHint, llmModelName)
        : replyRuntimeLabel(runtimeEngine, llmModelName);
      return (
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <div className="flex flex-col min-w-0">
            <span className="text-xs font-bold text-on-surface leading-tight">{agentTitle}</span>
            {(engineLabel || statusHint) && (
              <span className="text-[10px] text-on-surface-variant/60 leading-tight truncate">
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

  return (
    <section
      style={{
        paddingLeft: `${selectedSidebarWidth + 30}px`,
        paddingRight: `${rightSidebarWidth + 30}px`,
      }}
      className="mt-[64px] flex-1 overflow-y-auto py-10 pb-40 flex flex-col items-center px-6 transition-all duration-300 bg-background"
    >
      <div className="w-full max-w-2xl mx-auto space-y-8 py-4">
        {showEmptyState && (
          <div className="flex flex-col items-center justify-center text-center py-16 px-6 space-y-5">
            <div className="w-14 h-14 rounded-2xl bg-surface-container-low border border-outline-variant/40 flex items-center justify-center">
              <span className="material-symbols-outlined text-[28px] text-on-surface-variant">hub</span>
            </div>
            <div className="space-y-2 max-w-md">
              <h2
                data-testid="chat-supervised-title"
                className="text-lg font-bold text-on-surface tracking-tight"
              >
                {t('Start a supervised session')}
              </h2>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                {t('Select a workspace and start a workflow, or type an instruction below. Clutch will orchestrate Builder / Evaluator and ask for your approval when needed.')}
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
              {workspaceAuthorized && (
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

        {messages.map((msg) => {
          const isUser = msg.agent === 'User';
          const parsed = parseChatContent(msg.text);
          const displayText = parsed.text;
          const isErrorMsg =
            msg.status === 'FAILED' ||
            msg.badgeText?.includes('FAILED') ||
            msg.badgeText?.includes('NEEDS');
          const isCompletedMsg = msg.status === 'COMPLETED';

          return (
            <div
              key={msg.id}
              className={`w-full flex ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`flex gap-4 max-w-[85%] group hover:bg-surface-container-low/35 p-2 rounded-xl transition-colors ${
                  isUser ? 'flex-row-reverse' : ''
                }`}
              >
                <div className="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center bg-surface-container">
                  {msg.avatar ? (
                    <img className="w-full h-full object-cover" src={msg.avatar} alt={msg.agent} />
                  ) : (
                    <span className="material-symbols-outlined text-[18px] text-on-surface-variant">
                      {msg.agent === 'Supervisor'
                        ? 'verified_user'
                        : msg.agent === 'User'
                          ? 'person'
                          : msg.agent === 'System'
                            ? 'info'
                            : 'smart_toy'}
                    </span>

                  )}
                </div>

                <div className="flex-1 space-y-1.5 overflow-hidden">
                  <div className={`flex items-center gap-2 ${isUser ? 'justify-end' : ''}`}>
                    {isUser ? (
                      <>
                        <span className="text-[10px] text-on-surface-variant/60">{msg.time}</span>
                        <span className="text-xs font-bold text-on-surface">{msg.agent}</span>
                      </>
                    ) : (
                      <div className={`flex items-center gap-2 ${isPlainLlmChat && isPlainLlmReply(msg.agent) ? 'items-start' : ''}`}>
                        {renderAgentLabel(msg.agent, undefined, msg.runtimeEngine)}
                        <span className="text-[10px] text-on-surface-variant/60 flex-shrink-0">{msg.time}</span>
                      </div>
                    )}
                  </div>

                  {isErrorMsg ? (
                    <div className="p-4 bg-neutral-50/50 rounded-2xl rounded-tl-none border border-neutral-200/80 shadow-xs">
                      <div className="flex items-center gap-1.5 mb-2 text-neutral-800 font-bold text-[11px]">
                        <span className="material-symbols-outlined text-[16px]">error</span>
                        <span>VALIDATION FAILED</span>
                      </div>
                      {renderMarkdown(msg.text)}
                    </div>
                  ) : (
                    <div className={`p-4 rounded-2xl border border-outline-variant/30 shadow-sm ${
                      isUser 
                        ? 'bg-primary/10 text-on-surface rounded-tr-none text-left' 
                        : 'bg-surface-container-low rounded-tl-none'
                    }`}>
                      {msg.badgeText ? (
                        <div className="flex items-center gap-1.5 mb-2 text-primary font-bold text-[11px]">
                          <span className="material-symbols-outlined text-[16px]">info</span>
                          <span>{msg.badgeText}</span>
                        </div>
                      ) : isCompletedMsg ? (
                        <div className="flex items-center gap-1.5 mb-2 text-green-600 font-bold text-[11px]">
                          <span className="material-symbols-outlined text-[16px]">check_circle</span>
                          <span>COMPLETED</span>
                        </div>
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
                      {renderMarkdown(displayText)}
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
                      {msg.codeHighlight && (
                        <div className="mt-3 flex items-center gap-2 py-2 px-3 bg-white/60 rounded-xl border border-outline-variant/30">
                          <span className="material-symbols-outlined text-green-500 text-[18px]">
                            check_circle
                          </span>
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

        {showThinking && (
          <div className="w-full flex justify-start">
            <div className="flex gap-4 max-w-[85%] p-2 rounded-xl">
              <div className="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center bg-surface-container">
                <span className="material-symbols-outlined text-[18px] text-on-surface-variant/70 animate-spin">
                  progress_activity
                </span>
              </div>

              <div className="flex-1 space-y-1.5 overflow-hidden">
                <div className="flex items-center gap-2">
                  {renderAgentLabel(activeAgentName || t('Clutch Agent'), t('Thinking...'), engineHint)}
                </div>

                <div className="p-4 bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 shadow-sm flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-on-surface/40 animate-typing-bounce" />
                  <div className="w-1.5 h-1.5 rounded-full bg-on-surface/40 animate-typing-bounce animation-delay-100" />
                  <div className="w-1.5 h-1.5 rounded-full bg-on-surface/40 animate-typing-bounce animation-delay-200" />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div
        style={{
          left: `${selectedSidebarWidth + 24}px`,
          right: `${rightSidebarWidth + 24}px`,
        }}
        className="fixed bottom-8 flex justify-center px-6 z-40 transition-all duration-300 select-none"
      >
        {isRunning && !awaitingHuman && !isPlainLlmChat ? (
          <div className="w-full max-w-2xl bg-white border border-outline-variant p-3 shadow-xl rounded-xl flex items-center justify-between">
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
              <span className="material-symbols-outlined text-[13px]">cancel</span>
              Stop
            </button>
          </div>
        ) : awaitingHuman ? (
          <div className="w-full max-w-2xl bg-white border border-rose-200/90 p-5 shadow-xl rounded-2xl flex flex-col gap-4 text-left">
            <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
              <div className="flex items-center gap-2.5">
                <span
                  className="w-8 h-8 rounded-full text-white flex items-center justify-center"
                  style={{ backgroundColor: '#ba1a1a' }}
                >
                  <span className="material-symbols-outlined text-[18px]">gavel</span>
                </span>
                <div>
                  <h4 className="text-[11.5px] font-bold tracking-wider text-rose-800 uppercase">
                    Human-In-The-Loop
                  </h4>
                  <p className="text-[10.5px] text-on-surface-variant/80 mt-0.5">
                    {t('Human gate hint')}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                data-testid="chat-approve"
                onClick={onApprove}
                className={BTN_SUCCESS_SM}
              >
                Bypass & Approve
              </button>
              <button
                type="button"
                data-testid="chat-reject"
                onClick={onReject}
                className={BTN_DANGER_SM}
              >
                Reject & Redo
              </button>
            </div>
            <div className="flex items-center gap-2 bg-neutral-50 border border-neutral-200/80 p-1.5 rounded-xl">
              <input
                type="text"
                value={hillInstructions}
                onChange={(e) => setHillInstructions(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && hillInstructions.trim()) {
                    onRetryWithInstructions?.(hillInstructions.trim());
                    setHillInstructions('');
                  }
                }}
                placeholder={t('Retry instructions placeholder')}
                className="w-full bg-transparent border-none text-[11px] text-on-surface placeholder:text-neutral-400 focus:outline-none py-1.5 px-2"
              />
              <button
                type="button"
                disabled={!hillInstructions.trim()}
                onClick={() => {
                  if (hillInstructions.trim()) {
                    onRetryWithInstructions?.(hillInstructions.trim());
                    setHillInstructions('');
                  }
                }}
                className={`${BTN_SM} ${
                  hillInstructions.trim()
                    ? 'bg-neutral-900 text-white'
                    : 'bg-neutral-100 text-neutral-400 cursor-not-allowed'
                }`}
              >
                Retry
              </button>
            </div>
          </div>
        ) : (
          <div className="w-full flex justify-center">
            <ChatInputBar
              inputValue={inputValue}
              setInputValue={setInputValue}
              onSendMessage={handleSendWithAttachments}
              isRunning={isRunning}
              isPlainLlmChat={isPlainLlmChat}
              onStopRun={onStopRun}
              selectedWorkflowId={selectedWorkflowId}
              selectedWorkflowName={selectedWorkflowName}
              onClearSelectedWorkflow={onClearSelectedWorkflow}
              isMultiAgent={isMultiAgent}
              workspaceFiles={workspaceFiles}
              sessions={sessions}
              skills={skills}
              permissionMode={permissionMode}
              onPermissionModeChange={onPermissionModeChange ?? (() => {})}
            />
          </div>
        )}
      </div>
    </section>
  );
};
