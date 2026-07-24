/**
 * D3 / D49 — in-chat todo checklist (from todo_write / agent_todos).
 * While any item is incomplete, ChatFeed pins a Cursor-style card at the chat top;
 * when all items are completed it unpins and scrolls with the sealed message.
 */
import React from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import type { TodoItem } from '../types';
import {
  CHAT_AGENT_CARD,
  CHAT_AGENT_CARD_LIVE,
  ChatAgentCardHeader,
} from './chatAgentCard';

function statusIcon(status: TodoItem['status']): string {
  if (status === 'completed') return 'check_circle';
  if (status === 'in_progress') return 'progress_activity';
  return 'check_box_outline_blank';
}

function statusClass(status: TodoItem['status']): string {
  if (status === 'completed') return 'text-green-600';
  if (status === 'in_progress') return 'text-primary';
  return 'text-on-surface-variant/55';
}

/** True when every todo is completed (empty list → false). */
export function todosAreComplete(todos: TodoItem[]): boolean {
  return todos.length > 0 && todos.every((item) => item.status === 'completed');
}

function PinnedStatusIcon({ status }: { status: TodoItem['status'] }) {
  if (status === 'completed') {
    return (
      <LegacyIcon
        name="check_circle"
        className="mt-0.5 h-4 w-4 shrink-0 text-[16px] text-on-surface-variant/40"
      />
    );
  }
  if (status === 'in_progress') {
    return (
      <span
        className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-white"
        aria-hidden
      >
        <LegacyIcon name="chevron_right" className="text-[11px] leading-none" />
      </span>
    );
  }
  return (
    <span
      className="mt-0.5 h-4 w-4 shrink-0 rounded-full border border-on-surface-variant/30"
      aria-hidden
    />
  );
}

export function TodoCardView({
  todos,
  t,
  live,
  pinned,
}: {
  todos: TodoItem[];
  t: (key: string) => string;
  live?: boolean;
  /** Floating pin chrome — matches Cursor plan checklist (no gray header bar). */
  pinned?: boolean;
}) {
  if (!todos.length) return null;
  const done = todos.filter((item) => item.status === 'completed').length;

  if (pinned) {
    return (
      <div
        className="rounded-xl border border-neutral-200/90 bg-white shadow-sm overflow-hidden"
        data-testid="todo-card"
        data-live="true"
        data-pinned="true"
      >
        <div className="flex items-center gap-2 px-3.5 pt-3 pb-1">
          <span className="text-[13px] font-semibold text-on-surface truncate flex-1 min-w-0">
            {t('Todos')}
          </span>
          <span className="text-[11px] font-medium tabular-nums font-mono text-on-surface-variant/55 shrink-0">
            {done}/{todos.length}
          </span>
        </div>
        <ul className="px-3.5 pb-3 pt-1.5 space-y-2">
          {todos.map((item) => (
            <li key={item.id} className="flex items-start gap-2.5 text-[12.5px] leading-snug">
              <PinnedStatusIcon status={item.status} />
              <span
                className={
                  item.status === 'completed'
                    ? 'text-on-surface-variant/50 line-through'
                    : item.status === 'in_progress'
                      ? 'text-on-surface font-semibold'
                      : 'text-on-surface/80'
                }
              >
                {item.content}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div
      className={live ? CHAT_AGENT_CARD_LIVE : CHAT_AGENT_CARD}
      data-testid="todo-card"
      data-live={live ? 'true' : 'false'}
    >
      <ChatAgentCardHeader
        icon="checklist"
        title={t('Todos')}
        status={
          <span className="text-[10px] font-semibold tabular-nums font-mono text-on-surface-variant/70">
            {done}/{todos.length}
          </span>
        }
      />
      <ul className="px-3 py-2.5 space-y-1.5">
        {todos.map((item) => (
          <li key={item.id} className="flex items-start gap-2 text-[12px] leading-snug">
            <LegacyIcon
              name={statusIcon(item.status)}
              className={`text-[15px] mt-0.5 flex-shrink-0 ${statusClass(item.status)}`}
            />
            <span
              className={
                item.status === 'completed'
                  ? 'text-on-surface-variant line-through'
                  : item.status === 'in_progress'
                    ? 'text-on-surface font-semibold'
                    : 'text-on-surface'
              }
            >
              {item.content}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
