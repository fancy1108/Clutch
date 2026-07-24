/**
 * D49 — in-chat plan card (D2). Actions live on the Chat dock only.
 */
import React from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import type { PlanCard as PlanCardData } from '../types';

export function PlanCardView({
  card,
  t,
}: {
  card: PlanCardData;
  t: (key: string) => string;
}) {
  const status = card.status;
  const statusLabel =
    status === 'approved'
      ? t('Plan approved')
      : status === 'cancelled'
        ? t('Plan cancelled')
        : status === 'revised'
          ? t('Plan revision requested')
          : t('Awaiting plan approval');

  return (
    <div
      className="mt-2 rounded-xl border border-outline-variant/40 bg-white/80 overflow-hidden"
      data-testid="plan-card"
      data-status={status}
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b border-outline-variant/25 bg-surface-container-low/80">
        <LegacyIcon name="checklist" className="text-[16px] text-primary flex-shrink-0" />
        <span className="text-[12px] font-bold text-on-surface truncate flex-1">{card.title}</span>
        <span className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant/70 shrink-0">
          {statusLabel}
        </span>
      </div>
      {card.summary ? (
        <p className="px-3 pt-2 text-[11px] text-on-surface-variant leading-relaxed">{card.summary}</p>
      ) : null}
      <ol className="px-3 py-2 space-y-1 list-decimal list-inside">
        {card.steps.map((step, index) => (
          <li key={`${index}-${step.slice(0, 24)}`} className="text-[12px] text-on-surface leading-snug">
            {step}
          </li>
        ))}
      </ol>
      {card.note ? (
        <p className="px-3 pb-2 text-[11px] text-on-surface-variant italic">{card.note}</p>
      ) : null}
    </div>
  );
}
