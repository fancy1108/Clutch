/**
 * Shared chrome for in-chat agent cards (Plan / Question / Todo).
 * Tokens follow docs/UI_UX_GUIDELINES.md §2 · §4.1 · §4.4 · §6.
 */
import React from 'react';
import { ChevronRight } from 'lucide-react';
import { LegacyIcon } from './ui/LegacyIcon';

/** Card shell without vertical margin — sticky pins / custom spacing. */
export const CHAT_AGENT_CARD_SHELL =
  'rounded-xl border border-outline-variant/30 bg-white shadow-sm overflow-hidden';

export const CHAT_AGENT_CARD = `mt-2 ${CHAT_AGENT_CARD_SHELL}`;

export const CHAT_AGENT_CARD_LIVE = `mb-3 ${CHAT_AGENT_CARD_SHELL}`;

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
  expanded,
  onToggle,
  toggleLabel,
}: {
  icon: string;
  title: React.ReactNode;
  status?: React.ReactNode;
  /** With `onToggle`, renders a lucide disclosure chevron (§6). */
  expanded?: boolean;
  onToggle?: () => void;
  toggleLabel?: string;
}) {
  const interactive = typeof onToggle === 'function';
  const content = (
    <>
      {interactive ? (
        <ChevronRight
          className={`h-3.5 w-3.5 shrink-0 text-on-surface-variant/60 transition-transform duration-300 ${
            expanded ? 'rotate-90' : ''
          }`}
          strokeWidth={2}
          aria-hidden
        />
      ) : null}
      <LegacyIcon name={icon} className="text-[16px] text-primary flex-shrink-0" />
      <span className="text-[12px] font-bold text-on-surface truncate flex-1 min-w-0">{title}</span>
      {status}
    </>
  );

  if (interactive) {
    return (
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-label={toggleLabel}
        data-testid="chat-agent-card-toggle"
        className={`${CHAT_AGENT_CARD_HEADER} w-full text-left hover:bg-surface-container transition-all duration-300`}
      >
        {content}
      </button>
    );
  }

  return <div className={CHAT_AGENT_CARD_HEADER}>{content}</div>;
}
