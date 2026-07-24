/**
 * D3 / D49 — in-chat todo checklist (from todo_write / agent_todos).
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

export function TodoCardView({
  todos,
  t,
  live,
}: {
  todos: TodoItem[];
  t: (key: string) => string;
  live?: boolean;
}) {
  if (!todos.length) return null;
  const done = todos.filter((item) => item.status === 'completed').length;

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
