/**
 * Shared chrome for in-chat agent cards (Plan / Question / Todo).
 * Tokens follow docs/UI_UX_GUIDELINES.md §2 · §4.1 · §4.4.
 */
import React from 'react';
import { LegacyIcon } from './ui/LegacyIcon';

export const CHAT_AGENT_CARD =
  'mt-2 rounded-xl border border-outline-variant/30 bg-white shadow-sm overflow-hidden';

export const CHAT_AGENT_CARD_LIVE =
  'mb-3 rounded-xl border border-outline-variant/30 bg-white shadow-sm overflow-hidden';

export const CHAT_AGENT_CARD_HEADER =
  'flex items-center gap-2 px-3 py-2 border-b border-outline-variant/25 bg-surface-container-low';

export type ChatCardStatusTone = 'pending' | 'success' | 'danger' | 'muted';

const STATUS_TONE: Record<ChatCardStatusTone, string> = {
  pending: 'bg-surface-container-high text-primary',
  success: 'bg-emerald-50 text-emerald-800 border border-emerald-200/80',
  danger: 'bg-rose-50 text-rose-800 border border-rose-200/80',
  muted: 'bg-surface-container-high text-on-surface-variant/70',
};

export function ChatAgentCardStatus({
  tone,
  children,
}: {
  tone: ChatCardStatusTone;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`text-[10px] font-bold uppercase tracking-wider shrink-0 rounded-md px-1.5 py-0.5 ${STATUS_TONE[tone]}`}
    >
      {children}
    </span>
  );
}

export function ChatAgentCardHeader({
  icon,
  title,
  status,
}: {
  icon: string;
  title: React.ReactNode;
  status?: React.ReactNode;
}) {
  return (
    <div className={CHAT_AGENT_CARD_HEADER}>
      <LegacyIcon name={icon} className="text-[16px] text-primary flex-shrink-0" />
      <span className="text-[12px] font-bold text-on-surface truncate flex-1 min-w-0">{title}</span>
      {status}
    </div>
  );
}
