/**
 * D49 — in-chat plan card (D2). Actions live on the Chat dock only.
 * D31 — per-step inline comments on pending plans.
 */
import React from 'react';
import type { PlanCard as PlanCardData } from '../types';
import {
  CHAT_AGENT_CARD,
  ChatAgentCardHeader,
  ChatAgentCardStatus,
  type ChatCardStatusTone,
} from './chatAgentCard';

/** Strip model-supplied "1." / "1)" (repeat) so UI does not show "1. 1. …". */
export function stripPlanStepIndex(step: string): string {
  let cleaned = step.trim();
  for (let i = 0; i < 4; i++) {
    const next = cleaned.replace(/^\s*(?:\d+[\.\)\:．、]\s*|\d+\s+)/, '').trim();
    if (next === cleaned) break;
    cleaned = next;
  }
  return cleaned || step.trim();
}

export type PlanStepComment = { step: number; text: string; comment: string };

/** Build JSON revise payload for plan approval with per-step notes (D31). */
export function formatPlanRevisePayload(
  note: string,
  steps: string[],
  stepComments: string[],
): string {
  const annotations: PlanStepComment[] = [];
  for (let i = 0; i < steps.length; i += 1) {
    const comment = (stepComments[i] ?? '').trim();
    if (!comment) continue;
    annotations.push({
      step: i + 1,
      text: stripPlanStepIndex(steps[i] ?? ''),
      comment,
    });
  }
  return JSON.stringify({
    note: note.trim(),
    stepComments: annotations,
  });
}

export function hasPlanStepComments(stepComments: string[]): boolean {
  return stepComments.some((value) => value.trim().length > 0);
}

function statusTone(status: PlanCardData['status']): ChatCardStatusTone {
  if (status === 'approved') return 'success';
  if (status === 'cancelled') return 'danger';
  if (status === 'revised') return 'muted';
  return 'pending';
}

export function PlanCardView({
  card,
  t,
  stepComments,
  onStepCommentChange,
}: {
  card: PlanCardData;
  t: (key: string) => string;
  stepComments?: string[];
  onStepCommentChange?: (index: number, value: string) => void;
}) {
  const status = card.status;
  const pending = status === 'pending';
  const savedComments = card.stepComments ?? [];
  const statusLabel =
    status === 'approved'
      ? t('Plan approved')
      : status === 'cancelled'
        ? t('Plan cancelled')
        : status === 'revised'
          ? t('Plan revision requested')
          : t('Awaiting plan approval');

  return (
    <div className={CHAT_AGENT_CARD} data-testid="plan-card" data-status={status}>
      <ChatAgentCardHeader
        icon="checklist"
        title={card.title}
        status={<ChatAgentCardStatus tone={statusTone(status)}>{statusLabel}</ChatAgentCardStatus>}
      />
      {card.summary ? (
        <p className="px-3 pt-2 text-[11px] text-on-surface-variant leading-relaxed">{card.summary}</p>
      ) : null}
      {pending ? (
        <p className="px-3 pt-2 text-[11px] text-on-surface-variant leading-relaxed">
          {t('Approve, revise, or cancel in the bar below')}
        </p>
      ) : null}
      <ol className="px-3 py-2.5 space-y-2 list-none">
        {card.steps.map((step, index) => (
          <li
            key={`${index}-${step.slice(0, 24)}`}
            className="text-[12px] text-on-surface leading-snug"
          >
            <div className="flex gap-2">
              <span className="tabular-nums font-mono text-[11px] text-on-surface-variant/70 shrink-0 w-4 text-right">
                {index + 1}.
              </span>
              <span className="min-w-0 flex-1">{stripPlanStepIndex(step)}</span>
            </div>
            {pending && onStepCommentChange ? (
              <input
                type="text"
                data-testid={`plan-step-comment-${index}`}
                value={stepComments?.[index] ?? ''}
                onChange={(e) => onStepCommentChange(index, e.target.value)}
                placeholder={t('Comment on this step…')}
                className="mt-1 ml-6 w-[calc(100%-1.5rem)] rounded-md border border-outline-variant/30 bg-surface-container-low px-2 py-1 text-[11px] text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-1 focus:ring-neutral-900/15"
              />
            ) : null}
            {!pending && savedComments[index]?.trim() ? (
              <p className="mt-1 ml-6 text-[11px] text-on-surface-variant italic">
                {savedComments[index]}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
      {card.note ? (
        <p className="px-3 pb-3 text-[11px] text-on-surface-variant italic">{card.note}</p>
      ) : null}
    </div>
  );
}
