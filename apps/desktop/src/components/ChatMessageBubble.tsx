import React, { useState } from 'react';
import { ChevronRight, Loader2 } from 'lucide-react';
import {
  ChatMessage,
  HybridExecutionPayload,
  OutputEvent,
  QuestionOption,
  ToolStep,
} from '../types';
import { USER_CHAT_AVATAR } from '../services/clutchState';
import { clutchMarkUrl } from '../assets/brand';
import { resolveBrandLogoSrc } from '../services/brandLogos';
import { AgentChatAvatar } from './AgentChatAvatar';
import { ChatBubbleVideo } from './ChatBubbleVideo';
import { AgentLiveActivity } from './AgentLiveActivity';
import { FilesChangedChips } from './FilesChangedChips';
import { PlanCardView } from './PlanCardView';
import { QuestionCardView } from './QuestionCardView';
import { TodoCardView } from './TodoCardView';
import { SubtaskCardView } from './SubtaskCardView';
import { BackgroundJobChip } from './BackgroundJobsBar';
import { VerificationReportCardView } from './VerificationReportCardView';
import { DiffSummaryCardView } from './DiffSummaryCardView';
import { LegacyIcon } from './ui/LegacyIcon';
import type { chatChromeForHost } from '../platform/chrome/chatChrome';

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

export function isHybridReply(msg: ChatMessage): boolean {
  return Boolean(msg.runtimeEngine?.includes('Hybrid'));
}

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

const WORKFLOW_AGENTS = new Set(['Builder', 'Orchestrator', 'Evaluator', 'Supervisor']);

function isPlainLlmReply(agent: string): boolean {
  return agent !== 'User' && agent !== 'System' && !WORKFLOW_AGENTS.has(agent);
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

export function AgentMessageLabel({
  agent,
  statusHint,
  runtimeEngine,
  workflowAgentType,
  isPlainLlmChat,
  activeAgentName,
  llmModelName,
  engineHint,
  t,
}: {
  agent: string;
  statusHint?: string;
  runtimeEngine?: string;
  workflowAgentType?: string;
  isPlainLlmChat: boolean;
  activeAgentName: string;
  llmModelName: string;
  engineHint: string;
  t: (key: string) => string;
}) {
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
          <span
            className="text-[10px] text-on-surface-variant/70 flex-shrink-0 inline-flex items-center gap-1.5"
            data-testid="agent-live-status"
          >
            {(statusHint === t('Working…') ||
              statusHint === t('Thinking...') ||
              statusHint === t('Queued for shell...')) && (
              <Loader2
                className="h-3 w-3 text-primary animate-spin motion-reduce:animate-none"
                strokeWidth={2}
                aria-hidden
              />
            )}
            <span
              className={
                statusHint === t('Working…') || statusHint === t('Thinking...')
                  ? 'text-primary font-semibold'
                  : undefined
              }
            >
              {statusHint}
            </span>
          </span>
        )}
      </div>
    );
  }

  return (
    <>
      <span className="text-xs font-bold text-on-surface">{agent}</span>
      {statusHint && (
        <span
          className="text-[10px] text-on-surface-variant/70 inline-flex items-center gap-1.5"
          data-testid="agent-live-status"
        >
          {(statusHint === t('Working…') || statusHint === t('Thinking...')) && (
            <Loader2
              className="h-3 w-3 text-primary animate-spin motion-reduce:animate-none"
              strokeWidth={2}
              aria-hidden
            />
          )}
          {statusHint}
        </span>
      )}
    </>
  );
}

export interface ChatMessageBubbleRowProps {
  msg: ChatMessage;
  messageIndex: number;
  chatChrome: ReturnType<typeof chatChromeForHost>;
  t: (key: string) => string;
  renderMarkdown: (text: string) => React.ReactNode;
  isPlainLlmChat: boolean;
  llmModelName: string;
  userName: string;
  userAvatar?: string;
  hybridExecutions?: Record<string, HybridExecutionPayload>;
  workflowAgentSteps: Array<{ nodeId: string; agentName: string; agentType: string; toolId?: string; agentRef?: string; label?: string }>;
  workflowReplyStepIndex: Map<string, number>;
  resolveAgentLogo?: (agentName: string) => string | undefined;
  onOpenWorkspaceFile?: (path: string) => void;
  onViewToolStepInTerminal?: (step: ToolStep) => void;
  onContextMenu: (e: React.MouseEvent, messageId: string, messageIndex: number) => void;
  awaitingPlan: boolean;
  pendingPlanMessage: ChatMessage | null;
  planStepComments?: string[];
  onPlanStepCommentChange?: (index: number, value: string) => void;
  awaitingHuman: boolean;
  pendingQuestionMessage: ChatMessage | null;
  hitlBusy: boolean;
  setHitlBusy: (busy: boolean) => void;
  onAnswerQuestion?: (option: QuestionOption) => void;
  activeAgentName: string;
}

export function ChatMessageBubbleRow({
  msg,
  messageIndex,
  chatChrome,
  t,
  renderMarkdown,
  isPlainLlmChat,
  llmModelName,
  userName,
  userAvatar,
  hybridExecutions,
  workflowAgentSteps,
  workflowReplyStepIndex,
  resolveAgentLogo,
  onOpenWorkspaceFile,
  onViewToolStepInTerminal,
  onContextMenu,
  awaitingPlan,
  pendingPlanMessage,
  planStepComments,
  onPlanStepCommentChange,
  awaitingHuman,
  pendingQuestionMessage,
  hitlBusy,
  setHitlBusy,
  onAnswerQuestion,
  activeAgentName,
}: ChatMessageBubbleRowProps) {
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
  const isCompactionDigest =
    msg.agent === 'System' &&
    (msg.id.startsWith('system_digest_') ||
      Boolean(
        msg.badgeText?.includes('压缩') || msg.badgeText?.includes('COMPACTION'),
      ));
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
        onContextMenu={(e) => onContextMenu(e, msg.id, messageIndex)}
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
      onContextMenu={(e) => onContextMenu(e, msg.id, messageIndex)}
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
                <AgentMessageLabel
                  agent={msg.agent}
                  runtimeEngine={msg.runtimeEngine}
                  workflowAgentType={workflowReplyType}
                  isPlainLlmChat={isPlainLlmChat}
                  activeAgentName={activeAgentName}
                  llmModelName={llmModelName}
                  engineHint=""
                  t={t}
                />
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
              data-testid={isCompactionDigest ? 'compaction-digest' : undefined}
              className={`${chatChrome.messageBubblePaddingClass} rounded-2xl border shadow-sm ${
              isUser
                ? 'bg-primary/10 text-on-surface rounded-tr-none text-left border-outline-variant/30'
                : isCompactionDigest
                  ? 'bg-amber-50 border-amber-300/80 rounded-tl-none ring-1 ring-amber-200/80'
                  : 'bg-surface-container-low rounded-tl-none border-outline-variant/30'
            }`}>
              {msg.badgeText ? (
                <div
                  className={`flex items-center gap-1.5 mb-2 font-bold text-[11px] ${
                    isCompactionDigest
                      ? 'text-amber-800 tracking-wide'
                      : 'text-primary'
                  }`}
                >
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
                      ? onPlanStepCommentChange
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
              {!isUser && msg.bgJob ? (
                <BackgroundJobChip job={msg.bgJob} t={t} variant="feed" />
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
}
