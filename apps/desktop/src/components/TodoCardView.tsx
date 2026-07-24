/**
 * D3 / D49 — in-chat todo checklist (from todo_write / agent_todos).
 */
import React from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import type { TodoItem } from '../types';

function statusIcon(status: TodoItem['status']): string {
  if (status === 'completed') return 'check_circle';
  if (status === 'in_progress') return 'pending';
  return 'radio_button_unchecked';
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
      className={`${live ? 'mb-3' : 'mt-2'} rounded-xl border border-outline-variant/40 bg-white/80 overflow-hidden`}
      data-testid="todo-card"
      data-live={live ? 'true' : 'false'}
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b border-outline-variant/25 bg-surface-container-low/80">
        <LegacyIcon name="checklist" className="text-[16px] text-primary flex-shrink-0" />
        <span className="text-[12px] font-bold text-on-surface flex-1">{t('Todos')}</span>
        <span className="text-[10px] font-semibold text-on-surface-variant/70">
          {done}/{todos.length}
        </span>
      </div>
      <ul className="px-3 py-2 space-y-1.5">
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
