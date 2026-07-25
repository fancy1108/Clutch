import React, { useMemo, useState } from 'react';
import { Check, ChevronRight, ShieldAlert, Terminal, X } from 'lucide-react';
import type { ToolStep } from '../types';
import {
  normalizeToolStepsForDisplay,
  parseToolStepDetail,
  type ParsedToolDetail,
  TOOL_TRAIL_PEEK,
  verbGroupHeaderLabel,
} from '../services/agentActivitySteps';
import { isTerminalSyncableStep } from '../services/chatTerminalSync';
import { useLanguage } from './LanguageContext';
import { InlineFileDiffCard } from './DiffSummaryCardView';

type AgentLiveActivityProps = {
  steps: ToolStep[];
  /** D19 — foldable model reasoning in the same live activity strip as D46. */
  reasoningContent?: string | null;
  /** Live turn: keep header reflecting running/awaiting verbs. */
  live?: boolean;
  /** Force expanded (e.g. while awaiting approval). */
  defaultOpen?: boolean;
  className?: string;
  onOpenFile?: (path: string) => void;
  /** D51 — jump to Terminal lane / matching log for tool steps. */
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
  // Running: quiet marker — the single live spinner lives on the agent label.
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

function ToolStepDetailPanel({
  parsed,
  t,
  onViewInTerminal,
}: {
  parsed: ParsedToolDetail;
  t: (key: string) => string;
  onViewInTerminal?: () => void;
}) {
  const hasTarget = Boolean(parsed.target);
  const hasBody = Boolean(parsed.body);
  if (!hasTarget && !hasBody && !onViewInTerminal) return null;

  return (
    <div
      data-testid="agent-tool-step-detail"
      className="mt-1 rounded-xl border border-outline-variant/30 bg-surface-container-low p-2.5 shadow-sm space-y-2.5"
    >
      {hasTarget ? (
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
            {t('Target')}
          </p>
          <p className="mt-1 text-[11px] leading-snug font-mono text-on-surface break-all">
            {parsed.target}
          </p>
        </div>
      ) : null}
      {hasBody ? (
        <div className="min-w-0">
          <div className="flex items-baseline gap-2 min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
              {parsed.isError ? t('Error') : t('Result')}
            </p>
            {parsed.meta ? (
              <span className="text-[10px] tabular-nums text-on-surface-variant truncate">
                {parsed.meta}
              </span>
            ) : null}
          </div>
          <pre
            className={`mt-1 max-h-40 overflow-y-auto whitespace-pre-wrap break-words rounded-lg border border-outline-variant/25 bg-white px-2 py-1.5 text-[11px] leading-relaxed font-mono ${
              parsed.isError ? 'text-rose-800' : 'text-on-surface'
            }`}
          >
            {parsed.body}
          </pre>
        </div>
      ) : null}
      {onViewInTerminal ? (
        <button
          type="button"
          data-testid="chat-view-in-terminal"
          onClick={onViewInTerminal}
          className="inline-flex items-center gap-1.5 rounded-md border border-outline-variant/40 bg-white px-2 py-1 text-[10px] font-semibold text-on-surface hover:bg-surface-container transition-colors duration-200"
        >
          <Terminal className="h-3 w-3 text-on-surface-variant" strokeWidth={2} aria-hidden />
          {t('View in Terminal')}
        </button>
      ) : null}
    </div>
  );
}

function ToolStepRow({
  step,
  showDetail,
  onToggleDetail,
  onViewInTerminal,
  t,
}: {
  step: ToolStep;
  showDetail: boolean;
  onToggleDetail: () => void;
  onViewInTerminal?: (step: ToolStep) => void;
  t: (key: string) => string;
}) {
  const parsed = parseToolStepDetail(step.detail);
  const hasExpandable = Boolean(parsed.target || parsed.body);
  const canSyncTerminal = Boolean(onViewInTerminal) && isTerminalSyncableStep(step);
  const active = step.status === 'running' || step.status === 'awaiting';

  return (
    <li
      className="min-w-0 rounded-lg px-1.5 py-1 hover:bg-surface-container-low/80 transition-colors duration-200"
      data-testid="agent-tool-step"
      data-status={step.status}
    >
      <button
        type="button"
        disabled={!hasExpandable}
        onClick={onToggleDetail}
        className="flex w-full min-w-0 items-center gap-2 text-left disabled:cursor-default"
        aria-expanded={showDetail}
        aria-label={
          hasExpandable
            ? `${step.title}. ${showDetail ? t('Hide details') : t('Show details')}`
            : step.title
        }
      >
        <span className="flex h-4 w-4 shrink-0 items-center justify-center" aria-hidden>
          <StepStatusIcon status={step.status} />
        </span>
        <span
          className={`min-w-0 flex-1 truncate text-[13px] leading-snug ${
            active
              ? 'font-medium text-on-surface'
              : step.status === 'failed'
                ? 'text-rose-800'
                : 'text-on-surface-variant'
          }`}
          title={step.title}
        >
          {step.title}
        </span>
      </button>
      {showDetail ? (
        <ToolStepDetailPanel
          parsed={parsed}
          t={t}
          onViewInTerminal={canSyncTerminal ? () => onViewInTerminal?.(step) : undefined}
        />
      ) : null}
    </li>
  );
}

/**
 * Grok/Cursor verb_group tool transcript (D46):
 * collapsed = summary header + peek lines; expand = full list; step click = detail.
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
  const [expanded, setExpanded] = useState(defaultOpen);
  const [reasoningOpen, setReasoningOpen] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);

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

  const needsToggle = trailSteps.length > TOOL_TRAIL_PEEK;
  // Collapsed: peek the *latest* steps (what just happened), like Cursor/Grok.
  const visibleSteps =
    expanded || !needsToggle
      ? trailSteps
      : trailSteps.slice(-TOOL_TRAIL_PEEK);
  const hiddenCount = Math.max(0, trailSteps.length - visibleSteps.length);

  if (!steps.length && !hasReasoning) return null;

  return (
    <div
      className={`min-w-0 ${className}`}
      role="status"
      aria-live={live ? 'polite' : undefined}
      aria-busy={live && !awaiting ? true : undefined}
      aria-label={awaiting ? t('Awaiting approval') : live ? t('Working…') : header}
      data-live={live ? 'true' : undefined}
    >
      {hasReasoning ? (
        <div className="mb-1" data-testid="agent-live-reasoning">
          <button
            type="button"
            onClick={() => setReasoningOpen((value) => !value)}
            className="flex w-full items-center gap-1.5 rounded-lg py-1 px-1.5 text-left text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors duration-200"
          >
            <ChevronRight
              className={`h-3.5 w-3.5 shrink-0 text-on-surface-variant transition-transform duration-200 motion-reduce:transition-none ${
                reasoningOpen ? 'rotate-90' : ''
              }`}
              strokeWidth={2}
            />
            <span className="text-[12px] font-medium">{t('Thinking')}</span>
          </button>
          {reasoningOpen ? (
            <pre className="mt-1 mb-1.5 max-h-40 overflow-y-auto whitespace-pre-wrap break-words rounded-xl border border-outline-variant/30 bg-surface-container-low px-2.5 py-2 text-[11px] leading-relaxed font-mono text-on-surface shadow-sm">
              {reasoningText}
            </pre>
          ) : null}
        </div>
      ) : null}

      {(trailSteps.length > 0 || awaiting) ? (
        <div className="min-w-0" data-testid="agent-tool-trail">
          <div className="flex w-full items-center gap-1.5 rounded-lg py-1 px-1.5">
            {needsToggle ? (
              <button
                type="button"
                onClick={() => {
                  setExpanded((value) => !value);
                  if (expanded) setDetailId(null);
                }}
                className="flex min-w-0 flex-1 items-center gap-1.5 text-left text-on-surface-variant hover:text-on-surface transition-colors duration-200"
                aria-expanded={expanded}
              >
                <ChevronRight
                  className={`h-3.5 w-3.5 shrink-0 text-on-surface-variant transition-transform duration-200 motion-reduce:transition-none ${
                    expanded ? 'rotate-90' : ''
                  }`}
                  strokeWidth={2}
                />
                <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-on-surface">
                  {header}
                </span>
              </button>
            ) : (
              <div className="flex min-w-0 flex-1 items-center gap-1.5">
                <span className="inline-flex h-3.5 w-3.5 shrink-0" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-on-surface">
                  {header}
                </span>
              </div>
            )}
            {awaiting ? (
              <span className="shrink-0 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-amber-900">
                {t('Awaiting approval')} {awaitingSteps.length}
              </span>
            ) : null}
            {needsToggle ? (
              <button
                type="button"
                onClick={() => {
                  setExpanded((value) => !value);
                  if (expanded) setDetailId(null);
                }}
                className="shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-semibold text-primary hover:bg-primary/10 transition-colors duration-200"
                aria-expanded={expanded}
              >
                {expanded
                  ? t('Show less')
                  : t('Show all ({n})').replace('{n}', String(trailSteps.length))}
              </button>
            ) : null}
          </div>

          {/* Collapsed: always peek a few humanized lines (Cursor/Grok). */}
          <ol className="mt-0.5 mb-0.5 space-y-0.5 pl-1">
            {visibleSteps.map((step) => (
              <ToolStepRow
                key={step.id}
                step={step}
                showDetail={detailId === step.id}
                onToggleDetail={() =>
                  setDetailId((current) => (current === step.id ? null : step.id))
                }
                onViewInTerminal={onViewInTerminal}
                t={t}
              />
            ))}
          </ol>

          {!expanded && hiddenCount > 0 ? (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="ml-7 mb-1 text-left text-[11px] font-semibold text-primary hover:underline"
            >
              {t('+{n} more').replace('{n}', String(hiddenCount))}
            </button>
          ) : null}
        </div>
      ) : null}

      {editDiffSteps.length > 0 ? (
        <div className="mt-1 space-y-0" data-testid="agent-edit-diff-stream">
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
    </div>
  );
};
