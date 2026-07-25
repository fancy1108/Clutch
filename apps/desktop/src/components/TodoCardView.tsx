/**
 * D3 / D49 — in-chat todo checklist (from todo_write / agent_todos).
 * While any item is incomplete, ChatFeed pins a card at the chat top;
 * when all items are completed it unpins and scrolls with the sealed message.
 * Collapse/expand uses shared chatAgentCard chrome (UI_UX_GUIDELINES §2 · §4.1 · §4.4 · §6).
 */
import React, { useState } from 'react';
import { Check, ChevronRight, Circle } from 'lucide-react';
import type { TodoItem } from '../types';
import {
  CHAT_AGENT_CARD,
  CHAT_AGENT_CARD_LIVE,
  CHAT_AGENT_CARD_SHELL,
  ChatAgentCardHeader,
} from './chatAgentCard';

/** True when every todo is completed (empty list → false). */
export function todosAreComplete(todos: TodoItem[]): boolean {
  return todos.length > 0 && todos.every((item) => item.status === 'completed');
}

/** Pin incomplete live todos while the agent turn is active or awaiting human. */
export function shouldPinLiveTodos(
  todos: TodoItem[],
  opts: { isRunning: boolean; awaitingHuman: boolean },
): boolean {
  return (
    todos.length > 0 &&
    !todosAreComplete(todos) &&
    (opts.isRunning || opts.awaitingHuman)
  );
}

export function todoProgressLabel(todos: TodoItem[]): string {
  const done = todos.filter((item) => item.status === 'completed').length;
  return `${done}/${todos.length}`;
}

export function todoCardShellClass(opts: { live?: boolean; pinned?: boolean }): string {
  if (opts.pinned) return CHAT_AGENT_CARD_SHELL;
  if (opts.live) return CHAT_AGENT_CARD_LIVE;
  return CHAT_AGENT_CARD;
}

function TodoStatusIcon({ status }: { status: TodoItem['status'] }) {
  if (status === 'completed') {
    return <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-600" strokeWidth={2.5} />;
  }
  if (status === 'in_progress') {
    return (
      <span
        className="mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full bg-neutral-900 text-white"
        aria-hidden
      >
        <ChevronRight className="h-2.5 w-2.5" strokeWidth={2.5} />
      </span>
    );
  }
  return <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-on-surface-variant/45" strokeWidth={1.75} />;
}

function itemTextClass(status: TodoItem['status']): string {
  if (status === 'completed') return 'text-on-surface-variant line-through';
  if (status === 'in_progress') return 'text-on-surface font-semibold';
  return 'text-on-surface';
}

export function TodoCardView({
  todos,
  t,
  live,
  pinned,
  /** Controlled expand (tests / hosts). Omit for internal default-open state. */
  expanded: expandedProp,
  onExpandedChange,
}: {
  todos: TodoItem[];
  t: (key: string) => string;
  live?: boolean;
  /** Sticky pin — same shell tokens, no vertical margin. */
  pinned?: boolean;
  expanded?: boolean;
  onExpandedChange?: (open: boolean) => void;
}) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(true);
  const controlled = typeof expandedProp === 'boolean';
  const open = controlled ? expandedProp : uncontrolledOpen;

  const setOpen = (next: boolean) => {
    if (!controlled) setUncontrolledOpen(next);
    onExpandedChange?.(next);
  };

  if (!todos.length) return null;
  const progress = todoProgressLabel(todos);
  const toggleLabel = `${open ? t('Collapse') : t('Expand')} ${t('Todos')}`;
  const shell = todoCardShellClass({ live, pinned });

  return (
    <div
      className={shell}
      data-testid="todo-card"
      data-live={live || pinned ? 'true' : 'false'}
      data-pinned={pinned ? 'true' : undefined}
      data-expanded={open ? 'true' : 'false'}
    >
      <ChatAgentCardHeader
        icon="checklist"
        title={t('Todos')}
        expanded={open}
        onToggle={() => setOpen(!open)}
        toggleLabel={toggleLabel}
        status={
          <span className="text-[10px] font-semibold tabular-nums font-mono text-on-surface-variant/70">
            {progress}
          </span>
        }
      />
      {open ? (
        <ul className="px-3 py-2.5 space-y-1.5" data-testid="todo-card-list">
          {todos.map((item) => (
            <li key={item.id} className="flex items-start gap-2 text-[12px] leading-snug">
              <TodoStatusIcon status={item.status} />
              <span className={itemTextClass(item.status)}>{item.content}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
