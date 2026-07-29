import React, { useMemo, useState } from 'react';
import { Check, ChevronRight, ShieldAlert, Terminal, X } from 'lucide-react';
import type { ToolStep } from '../types';
import {
  normalizeToolStepsForDisplay,
  parseToolStepDetail,
  type ParsedToolDetail,
  stepFocusLine,
  TOOL_TRAIL_PEEK,
  TOOL_TRAIL_PEEK_LIVE,
  verbGroupHeaderLabel,
} from '../services/agentActivitySteps';
import { isTerminalSyncableStep } from '../services/chatTerminalSync';
import { useLanguage } from './LanguageContext';
import { InlineFileDiffCard } from './DiffSummaryCardView';

type AgentLiveActivityProps = {
  steps: ToolStep[];
  /** D19 — foldable model reasoning in the same live activity strip as D46. */
  reasoningContent?: string | null;
  /** Live turn: keep Working footer. */
  live?: boolean;
  /** Force expanded (e.g. while awaiting approval). */
  defaultOpen?: boolean;
  className?: string;
  onOpenFile?: (path: string) => void;
  /** D51 — open right-rail Terminal and highlight matching audit log. */
  onViewInTerminal?: (step: ToolStep) => void;
};

function StepStatusIcon({ status }: { status: ToolStep['status'] }) {
  if (status === 'completed') {
    return <Check className="h-3.5 w-3.5 text-emerald-600" strokeWidth={2.5} />;
  }
  if (status === 'failed') {
    return <X className="h-3.5 w-3.5 text-rose-600" strokeWidth={2.5} />;
  }
  if (status === 'awaiting') {
    return <ShieldAlert className="h-3.5 w-3.5 text-amber-700" />;
  }
  return <span className="h-2 w-2 rounded-full bg-primary" aria-hidden />;
}

/** Typing dots for the pre-tool thinking bubble only (not the tool trail). */
export function TypingDots({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 ${className}`}
      aria-hidden
      data-testid="typing-dots"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-on-surface/45 animate-typing-pulse motion-reduce:animate-none" />
      <span className="w-1.5 h-1.5 rounded-full bg-on-surface/45 animate-typing-pulse animation-delay-100 motion-reduce:animate-none" />
      <span className="w-1.5 h-1.5 rounded-full bg-on-surface/45 animate-typing-pulse animation-delay-200 motion-reduce:animate-none" />
    </span>
  );
}

/** Compact result panel — capped height so expand does not thrash chat layout. */
function ToolStepResultPanel({
  parsed,
  t,
  onViewInTerminal,
}: {
  parsed: ParsedToolDetail;
  t: (key: string) => string;
  onViewInTerminal?: () => void;
}) {
  if (!parsed.body && !onViewInTerminal) return null;

  return (
    <div
      data-testid="agent-tool-step-detail"
      className="mt-1 ml-5 space-y-1.5"
    >
      {parsed.body ? (
        <pre
          className={`max-h-24 overflow-y-auto overscroll-contain whitespace-pre-wrap break-words rounded-lg bg-surface-container-low/80 px-2 py-1.5 text-[11px] leading-relaxed font-mono ${
            parsed.isError ? 'text-rose-800' : 'text-on-surface-variant'
          }`}
        >
          {parsed.body}
        </pre>
      ) : null}
      {onViewInTerminal ? (
        <button
          type="button"
          data-testid="chat-view-in-terminal"
          onClick={onViewInTerminal}
          className="inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-[10px] font-semibold text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low transition-colors duration-200"
        >
          <Terminal className="h-3 w-3" strokeWidth={2} aria-hidden />
          {t('View in Terminal')}
        </button>
      ) : null}
    </div>
  );
}

/**
 * Unified process row (live + sealed): title + optional focus line + optional result.
 * No heavy Target card — focus is always visible; expand only reveals result body.
 */
function ToolStepRow({
  step,
  showResult,
  onToggleResult,
  onViewInTerminal,
  t,
}: {
  step: ToolStep;
  showResult: boolean;
  onToggleResult: () => void;
  onViewInTerminal?: (step: ToolStep) => void;
  t: (key: string) => string;
}) {
  const parsed = parseToolStepDetail(step.detail);
  const focus = stepFocusLine(step);
  const hasResult = Boolean(parsed.body);
  const canSyncTerminal = Boolean(onViewInTerminal) && isTerminalSyncableStep(step);
  const active = step.status === 'running' || step.status === 'awaiting';
  const expandable = hasResult || canSyncTerminal;

  return (
    <li
      className="min-w-0"
      data-testid="agent-tool-step"
      data-status={step.status}
    >
      <button
        type="button"
        disabled={!expandable}
        onClick={onToggleResult}
        className="flex w-full min-w-0 items-start gap-2 py-0.5 text-left disabled:cursor-default"
        aria-expanded={expandable ? showResult : undefined}
        aria-label={
          expandable
            ? `${step.title}. ${showResult ? t('Hide details') : t('Show details')}`
            : step.title
        }
      >
        <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center" aria-hidden>
          <StepStatusIcon status={step.status} />
        </span>
        <span className="min-w-0 flex-1">
          <span
            className={`block truncate text-[13px] leading-snug ${
              active
                ? 'font-medium text-on-surface'
                : step.status === 'failed'
                  ? 'text-rose-700'
                  : 'text-on-surface-variant'
            }`}
            title={step.title}
          >
            {step.title}
          </span>
          {focus ? (
            <span
              className="mt-0.5 block truncate text-[11px] leading-snug text-on-surface-variant/70"
              title={focus}
              data-testid="agent-tool-focus"
            >
              {focus}
            </span>
          ) : null}
        </span>
        {expandable ? (
          <ChevronRight
            className={`mt-0.5 h-3.5 w-3.5 shrink-0 text-on-surface-variant/60 transition-transform duration-200 motion-reduce:transition-none ${
              showResult ? 'rotate-90' : ''
            }`}
            strokeWidth={2}
            aria-hidden
          />
        ) : null}
      </button>
      {showResult && expandable ? (
        <ToolStepResultPanel
          parsed={parsed}
          t={t}
          onViewInTerminal={canSyncTerminal ? () => onViewInTerminal?.(step) : undefined}
        />
      ) : null}
    </li>
  );
}

/**
 * Grok/Cursor process transcript (D46) — same chrome for live and sealed turns.
 */
export const AgentLiveActivity: React.FC<AgentLiveActivityProps> = ({
  steps,
  reasoningContent,
  live = false,
  defaultOpen = false,
  className = '',
  onOpenFile,
  onViewInTerminal,
}) => {
  const { t } = useLanguage();
  const [listExpanded, setListExpanded] = useState(defaultOpen || live);
  const [reasoningOpen, setReasoningOpen] = useState(false);
  const [resultId, setResultId] = useState<string | null>(null);

  const reasoningText = reasoningContent?.trim() ?? '';
  const hasReasoning = reasoningText.length > 0;

  const displaySteps = useMemo(() => normalizeToolStepsForDisplay(steps), [steps]);
  const editDiffSteps = displaySteps.filter(
    (step) => step.fileDiff && (step.status === 'completed' || step.status === 'failed'),
  );
  const trailSteps = displaySteps.filter((step) => !step.fileDiff);
  const header = verbGroupHeaderLabel(displaySteps) || t('Tools');
  const awaitingSteps = displaySteps.filter((step) => step.status === 'awaiting');
  const awaiting = awaitingSteps.length > 0;
  const peek = live ? TOOL_TRAIL_PEEK_LIVE : TOOL_TRAIL_PEEK;

  const needsToggle = trailSteps.length > peek;
  const visibleSteps =
    listExpanded || !needsToggle ? trailSteps : trailSteps.slice(-peek);
  const hiddenCount = Math.max(0, trailSteps.length - visibleSteps.length);

  if (!steps.length && !hasReasoning) return null;

  const toggleResult = (id: string) => {
    setResultId((current) => (current === id ? null : id));
  };

  return (
    <div
      className={`min-w-0 ${className}`}
      role="status"
      aria-live={live ? 'polite' : undefined}
      aria-busy={live && !awaiting ? true : undefined}
      aria-label={awaiting ? t('Awaiting approval') : live ? t('Working…') : header}
      data-live={live ? 'true' : undefined}
      data-testid={live ? 'agent-live-stream' : 'agent-tool-trail'}
    >
      {hasReasoning ? (
        <div className="mb-1.5" data-testid="agent-live-reasoning">
          <button
            type="button"
            onClick={() => setReasoningOpen((value) => !value)}
            className="flex w-full items-center gap-1.5 py-0.5 text-left text-on-surface-variant hover:text-on-surface transition-colors duration-200"
          >
            <ChevronRight
              className={`h-3.5 w-3.5 shrink-0 transition-transform duration-200 motion-reduce:transition-none ${
                reasoningOpen ? 'rotate-90' : ''
              }`}
              strokeWidth={2}
            />
            <span className="text-[13px]">{t('Thinking')}</span>
          </button>
          {reasoningOpen ? (
            <pre className="mt-1 max-h-28 overflow-y-auto overscroll-contain whitespace-pre-wrap break-words rounded-lg bg-surface-container-low/80 px-2.5 py-2 text-[11px] leading-relaxed font-mono text-on-surface-variant">
              {reasoningText}
            </pre>
          ) : null}
        </div>
      ) : null}

      {!live && trailSteps.length > 0 ? (
        <div className="mb-0.5 flex w-full items-center gap-1.5 py-0.5">
          {needsToggle ? (
            <button
              type="button"
              onClick={() => {
                setListExpanded((value) => !value);
                if (listExpanded) setResultId(null);
              }}
              className="flex min-w-0 flex-1 items-center gap-1.5 text-left text-on-surface-variant hover:text-on-surface transition-colors duration-200"
              aria-expanded={listExpanded}
            >
              <ChevronRight
                className={`h-3.5 w-3.5 shrink-0 transition-transform duration-200 motion-reduce:transition-none ${
                  listExpanded ? 'rotate-90' : ''
                }`}
                strokeWidth={2}
              />
              <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-on-surface">
                {header}
              </span>
            </button>
          ) : (
            <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-on-surface pl-5">
              {header}
            </span>
          )}
          {awaiting ? (
            <span className="shrink-0 text-[11px] font-medium text-amber-800">
              {t('Awaiting approval')}
            </span>
          ) : null}
        </div>
      ) : null}

      {trailSteps.length > 0 ? (
        <ol className="space-y-1" data-testid="agent-tool-trail-list">
          {visibleSteps.map((step) => (
            <ToolStepRow
              key={step.id}
              step={step}
              showResult={resultId === step.id}
              onToggleResult={() => toggleResult(step.id)}
              onViewInTerminal={onViewInTerminal}
              t={t}
            />
          ))}
        </ol>
      ) : null}

      {!listExpanded && hiddenCount > 0 ? (
        <button
          type="button"
          onClick={() => setListExpanded(true)}
          className="mt-1 ml-5 text-left text-[12px] font-medium text-primary hover:underline"
        >
          {t('+{n} more').replace('{n}', String(hiddenCount))}
        </button>
      ) : null}

      {editDiffSteps.length > 0 ? (
        <div className="mt-1.5 space-y-0" data-testid="agent-edit-diff-stream">
          {editDiffSteps.map((step) =>
            step.fileDiff ? (
              <InlineFileDiffCard
                key={`diff-${step.id}`}
                file={step.fileDiff}
                title={step.fileDiff.path.split(/[/\\]/).pop() || step.fileDiff.path}
                onOpenFile={onOpenFile}
              />
            ) : null,
          )}
        </div>
      ) : null}

      {live ? (
        awaiting ? (
          <p className="mt-1.5 text-[13px] font-medium text-amber-800" data-testid="agent-live-awaiting">
            {t('Awaiting approval')}
          </p>
        ) : (
          <p className="mt-1.5 text-[13px] text-on-surface-variant" data-testid="agent-live-working">
            {t('Working…')}
          </p>
        )
      ) : null}
    </div>
  );
};
