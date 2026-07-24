/**
 * D10 / D48 — nested subtask cards under a parent Chat bubble.
 */
import React, { useState } from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import type { SubtaskCard } from '../types';
import {
  CHAT_AGENT_CARD,
  CHAT_AGENT_CARD_LIVE,
  ChatAgentCardHeader,
  ChatAgentCardStatus,
  type ChatCardStatusTone,
} from './chatAgentCard';

function statusTone(status: SubtaskCard['status']): ChatCardStatusTone {
  if (status === 'done') return 'success';
  if (status === 'failed') return 'danger';
  return 'pending';
}

function statusLabel(status: SubtaskCard['status'], t: (key: string) => string): string {
  if (status === 'done') return t('Done');
  if (status === 'failed') return t('Failed');
  return t('Running');
}

function SubtaskCardItem({
  card,
  t,
}: {
  card: SubtaskCard;
  t: (key: string) => string;
}) {
  const [open, setOpen] = useState(card.status === 'failed');
  const steps = card.toolSteps ?? [];
  return (
    <div
      data-testid={`subtask-card-${card.id}`}
      className="rounded-lg border border-outline-variant/40 bg-surface-container-low/40 px-2.5 py-2"
    >
      <div className="flex items-start gap-2 min-w-0">
        <LegacyIcon
          name={card.type === 'explore' ? 'travel_explore' : 'construction'}
          className="text-[16px] text-on-surface-variant/70 mt-0.5 shrink-0"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[12px] font-semibold text-on-surface truncate">
              {card.title || (card.type === 'explore' ? t('Explore') : t('Implement'))}
            </span>
            <span className="text-[10px] uppercase tracking-wide text-on-surface-variant/55">
              {card.type}
            </span>
            <ChatAgentCardStatus tone={statusTone(card.status)}>
              {statusLabel(card.status, t)}
            </ChatAgentCardStatus>
          </div>
          {card.summary ? (
            <p className="mt-1 text-[11px] leading-snug text-on-surface-variant whitespace-pre-wrap break-words">
              {card.summary}
            </p>
          ) : null}
          {card.error && card.status === 'failed' ? (
            <p className="mt-1 text-[11px] text-rose-700 whitespace-pre-wrap break-words">
              {card.error}
            </p>
          ) : null}
          {steps.length > 0 ? (
            <button
              type="button"
              className="mt-1.5 text-[10px] font-semibold text-primary hover:underline"
              onClick={() => setOpen((v) => !v)}
            >
              {open ? t('Hide steps') : t('Show steps')} ({steps.length})
            </button>
          ) : null}
          {open && steps.length > 0 ? (
            <ul className="mt-1.5 space-y-0.5 pl-0.5">
              {steps.map((step, idx) => (
                <li
                  key={`${step.name}-${idx}`}
                  className="text-[10px] font-mono text-on-surface-variant/80 flex gap-1.5"
                >
                  <span className="shrink-0">{step.status === 'failed' ? '✗' : '·'}</span>
                  <span className="truncate">{step.name}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function SubtaskCardView({
  cards,
  t,
  live = false,
}: {
  cards: SubtaskCard[];
  t: (key: string) => string;
  live?: boolean;
}) {
  if (!cards.length) return null;
  return (
    <div
      data-testid="subtask-cards"
      className={live ? CHAT_AGENT_CARD_LIVE : CHAT_AGENT_CARD}
    >
      <ChatAgentCardHeader
        icon="account_tree"
        title={t('Subtasks')}
        status={
          cards.some((c) => c.status === 'failed') ? (
            <ChatAgentCardStatus tone="danger">{t('Failed')}</ChatAgentCardStatus>
          ) : cards.some((c) => c.status === 'running') ? (
            <ChatAgentCardStatus tone="pending">{t('Running')}</ChatAgentCardStatus>
          ) : (
            <ChatAgentCardStatus tone="success">{t('Done')}</ChatAgentCardStatus>
          )
        }
      />
      <div className="p-2.5 space-y-2">
        {cards.map((card) => (
          <SubtaskCardItem key={card.id} card={card} t={t} />
        ))}
      </div>
    </div>
  );
}
