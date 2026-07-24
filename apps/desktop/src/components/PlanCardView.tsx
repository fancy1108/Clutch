/**
 * D49 — in-chat plan card (D2). Actions live on the Chat dock only.
 * Chrome shared with Question/Todo — docs/UI_UX_GUIDELINES.md §4.1.
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

function statusTone(status: PlanCardData['status']): ChatCardStatusTone {
  if (status === 'approved') return 'success';
  if (status === 'cancelled') return 'danger';
  if (status === 'revised') return 'muted';
  return 'pending';
}

export function PlanCardView({
  card,
  t,
}: {
  card: PlanCardData;
  t: (key: string) => string;
}) {
  const status = card.status;
  const pending = status === 'pending';
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
      {/* Manual indices — avoid CSS list-decimal doubling model-supplied "1." */}
      <ol className="px-3 py-2.5 space-y-1.5 list-none">
        {card.steps.map((step, index) => (
          <li
            key={`${index}-${step.slice(0, 24)}`}
            className="text-[12px] text-on-surface leading-snug flex gap-2"
          >
            <span className="tabular-nums font-mono text-[11px] text-on-surface-variant/70 shrink-0 w-4 text-right">
              {index + 1}.
            </span>
            <span className="min-w-0 flex-1">{stripPlanStepIndex(step)}</span>
          </li>
        ))}
      </ol>
      {card.note ? (
        <p className="px-3 pb-3 text-[11px] text-on-surface-variant italic">{card.note}</p>
      ) : null}
    </div>
  );
}
