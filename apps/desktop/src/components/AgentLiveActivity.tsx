import React, { useState } from 'react';
import { Check, ChevronRight, Loader2, ShieldAlert, X } from 'lucide-react';
import type { ToolStep } from '../types';
import { verbGroupHeaderLabel } from '../services/agentActivitySteps';
import { useLanguage } from './LanguageContext';

type AgentLiveActivityProps = {
  steps: ToolStep[];
  /** Live turn: keep header reflecting running/awaiting verbs. */
  live?: boolean;
  /** Force expanded (e.g. while awaiting approval). */
  defaultOpen?: boolean;
  className?: string;
};

function StepStatusIcon({ status }: { status: ToolStep['status'] }) {
  if (status === 'completed') {
    return <Check className="h-3.5 w-3.5 text-emerald-600/90" strokeWidth={2.5} />;
  }
  if (status === 'failed') {
    return <X className="h-3.5 w-3.5 text-red-600/80" strokeWidth={2.5} />;
  }
  if (status === 'awaiting') {
    return <ShieldAlert className="h-3.5 w-3.5 text-amber-700/90" />;
  }
  return <Loader2 className="h-3.5 w-3.5 text-on-surface/50 animate-spin" />;
}

/**
 * Grok-style verb_group tool transcript (D46).
 * Collapsed header: "Read 2 files, Searched 1 pattern"; expand for step titles + detail.
 */
export const AgentLiveActivity: React.FC<AgentLiveActivityProps> = ({
  steps,
  live = false,
  defaultOpen = false,
  className = '',
}) => {
  const { t } = useLanguage();
  const [open, setOpen] = useState(defaultOpen);
  const [detailId, setDetailId] = useState<string | null>(null);

  if (!steps.length) return null;

  const header = verbGroupHeaderLabel(steps) || t('Tools');
  const awaitingSteps = steps.filter((step) => step.status === 'awaiting');
  const awaiting = awaitingSteps.length > 0;

  return (
    <div
      className={`min-w-0 ${className}`}
      role="status"
      aria-live={live ? 'polite' : undefined}
      aria-label={awaiting ? t('Awaiting approval') : header}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-1.5 rounded-md py-1 px-1 text-left text-on-surface-variant hover:bg-surface-container/70 hover:text-on-surface transition-colors"
      >
        <ChevronRight
          className={`h-3.5 w-3.5 shrink-0 text-on-surface-variant/60 transition-transform duration-200 ${
            open ? 'rotate-90' : ''
          }`}
          strokeWidth={2}
        />
        <span className="text-[11px] font-medium text-on-surface truncate">{header}</span>
        {awaiting ? (
          <span className="text-[10px] text-amber-800/80 shrink-0 tabular-nums">
            {t('Awaiting approval')} {awaitingSteps.length}
          </span>
        ) : null}
      </button>

      {open ? (
        <ol className="ml-[1.1rem] mt-0.5 mb-1 border-l border-outline-variant/25 pl-2.5 space-y-0.5">
          {steps.map((step) => {
            const showDetail = detailId === step.id && Boolean(step.detail);
            return (
              <li key={step.id} className="min-w-0">
                <button
                  type="button"
                  onClick={() =>
                    setDetailId((current) => (current === step.id ? null : step.id))
                  }
                  className="flex w-full items-center gap-2 rounded-md px-1 py-1 text-left hover:bg-surface-container/60 transition-colors"
                >
                  <span className="flex h-4 w-4 shrink-0 items-center justify-center" aria-hidden>
                    <StepStatusIcon status={step.status} />
                  </span>
                  <span
                    className={`min-w-0 flex-1 text-[12px] leading-snug break-words ${
                      step.status === 'completed' || step.status === 'failed'
                        ? 'text-on-surface-variant'
                        : 'text-on-surface font-medium'
                    }`}
                    title={step.detail || step.title}
                  >
                    {step.title}
                  </span>
                </button>
                {showDetail ? (
                  <pre className="ml-6 mb-1 whitespace-pre-wrap break-words text-[10px] leading-relaxed font-mono text-on-surface-variant/80 max-h-32 overflow-y-auto">
                    {step.detail}
                  </pre>
                ) : null}
              </li>
            );
          })}
        </ol>
      ) : null}
    </div>
  );
};
