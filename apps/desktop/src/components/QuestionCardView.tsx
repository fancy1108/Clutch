/**
 * D4 / D49 — in-chat multiple-choice question card (UI_UX_GUIDELINES §4).
 */
import React from 'react';
import type { QuestionCard as QuestionCardData, QuestionOption } from '../types';
import {
  CHAT_AGENT_CARD,
  ChatAgentCardHeader,
  ChatAgentCardStatus,
  type ChatCardStatusTone,
} from './chatAgentCard';
import { BTN_FOCUS } from './ui/buttonStyles';

const OPTION_LETTERS = 'ABCDEFGH';

function statusTone(status: QuestionCardData['status'], canChoose: boolean): ChatCardStatusTone {
  if (status === 'answered') return 'success';
  if (status === 'cancelled') return 'danger';
  if (canChoose) return 'pending';
  return 'muted';
}

export function QuestionCardView({
  card,
  t,
  interactive,
  onSelect,
}: {
  card: QuestionCardData;
  t: (key: string) => string;
  interactive?: boolean;
  onSelect?: (option: QuestionOption) => void;
}) {
  const status = card.status;
  const canChoose = Boolean(interactive && status === 'pending' && onSelect);
  const statusLabel =
    status === 'answered'
      ? t('Answered')
      : status === 'cancelled'
        ? t('Question cancelled')
        : t('Awaiting your choice');

  return (
    <div className={CHAT_AGENT_CARD} data-testid="question-card" data-status={status}>
      <ChatAgentCardHeader
        icon="forum"
        title={t('Question')}
        status={
          <ChatAgentCardStatus tone={statusTone(status, canChoose)}>
            {statusLabel}
          </ChatAgentCardStatus>
        }
      />

      <p className="px-3 pt-3 text-[13px] text-on-surface leading-relaxed font-semibold">
        {card.question}
      </p>
      {canChoose ? (
        <p className="px-3 pt-1 pb-2 text-[11px] text-on-surface-variant leading-relaxed">
          {t('Click an option below to continue')}
        </p>
      ) : (
        <div className="h-2" />
      )}

      <div className="px-3 pb-3 flex flex-col gap-2" role={canChoose ? 'listbox' : undefined}>
        {card.options.map((option, index) => {
          const selected =
            status === 'answered' &&
            (card.selectedId === option.id || card.selectedLabel === option.label);
          const letter = OPTION_LETTERS[index] ?? String(index + 1);

          if (canChoose) {
            return (
              <button
                key={option.id}
                type="button"
                role="option"
                data-testid={`question-option-${option.id}`}
                onClick={() => onSelect?.(option)}
                className={`${BTN_FOCUS} group w-full flex items-start gap-2.5 rounded-xl border border-neutral-200 bg-surface-container-low px-3 py-2.5 text-left transition-all duration-200 hover:border-neutral-900 hover:bg-white hover:shadow-sm active:scale-[0.99]`}
              >
                <span
                  className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-neutral-300 bg-white text-[10px] font-bold font-mono text-on-surface group-hover:border-neutral-900 group-hover:bg-neutral-900 group-hover:text-white transition-all duration-200"
                  aria-hidden
                >
                  {letter}
                </span>
                <span className="min-w-0 flex-1 text-[12px] leading-snug text-on-surface font-medium whitespace-normal">
                  {option.label}
                </span>
                <span className="mt-0.5 shrink-0 text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/50 group-hover:text-on-surface transition-colors duration-200">
                  {t('Select option')}
                </span>
              </button>
            );
          }

          return (
            <div
              key={option.id}
              data-testid={`question-option-${option.id}`}
              className={`w-full flex items-start gap-2.5 rounded-xl border px-3 py-2 text-left ${
                selected
                  ? 'border-neutral-900 bg-neutral-900 text-white'
                  : 'border-outline-variant/30 bg-surface-container-low/60 text-on-surface-variant'
              }`}
            >
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold font-mono ${
                  selected
                    ? 'bg-white text-neutral-900'
                    : 'border border-outline-variant/40 text-on-surface-variant/70'
                }`}
                aria-hidden
              >
                {selected ? '✓' : letter}
              </span>
              <span className="min-w-0 flex-1 text-[12px] leading-snug font-medium whitespace-normal">
                {option.label}
              </span>
            </div>
          );
        })}
      </div>

      {status === 'answered' && card.selectedLabel ? (
        <p className="px-3 pb-3 text-[11px] text-on-surface-variant">
          {t('Selected')}: {card.selectedLabel}
        </p>
      ) : null}
      {card.note ? (
        <p className="px-3 pb-3 text-[11px] text-on-surface-variant italic">{card.note}</p>
      ) : null}
    </div>
  );
}
