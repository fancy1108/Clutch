import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  TodoCardView,
  shouldPinLiveTodos,
  todoCardShellClass,
  todoProgressLabel,
  todosAreComplete,
} from './TodoCardView';
import {
  CHAT_AGENT_CARD,
  CHAT_AGENT_CARD_LIVE,
  CHAT_AGENT_CARD_SHELL,
} from './chatAgentCard';
import type { TodoItem } from '../types';

const item = (status: TodoItem['status'], id = status, content = id): TodoItem => ({
  id,
  content,
  status,
});

const t = (key: string) => key;

const sampleTodos: TodoItem[] = [
  item('completed', 'a', 'Ship D19'),
  item('in_progress', 'b', 'Ship D20'),
  item('pending', 'c', 'Ship D26'),
];

describe('todosAreComplete', () => {
  it('is false for an empty list', () => {
    expect(todosAreComplete([])).toBe(false);
  });

  it('is false while any item is pending or in_progress', () => {
    expect(todosAreComplete([item('completed', 'a'), item('pending', 'b')])).toBe(false);
    expect(todosAreComplete([item('in_progress')])).toBe(false);
  });

  it('is true only when every item is completed', () => {
    expect(todosAreComplete([item('completed', 'a'), item('completed', 'b')])).toBe(true);
  });
});

describe('todoProgressLabel', () => {
  it('formats done/total', () => {
    expect(todoProgressLabel(sampleTodos)).toBe('1/3');
    expect(todoProgressLabel([item('completed', 'a'), item('completed', 'b')])).toBe('2/2');
    expect(todoProgressLabel([item('pending', 'x')])).toBe('0/1');
  });
});

describe('todoCardShellClass', () => {
  it('uses shared shell tokens (UI_UX §2 / §4.1)', () => {
    expect(todoCardShellClass({ pinned: true })).toBe(CHAT_AGENT_CARD_SHELL);
    expect(todoCardShellClass({ live: true })).toBe(CHAT_AGENT_CARD_LIVE);
    expect(todoCardShellClass({})).toBe(CHAT_AGENT_CARD);
  });

  it('prefers pinned over live (no vertical margin on sticky rail)', () => {
    expect(todoCardShellClass({ pinned: true, live: true })).toBe(CHAT_AGENT_CARD_SHELL);
    expect(CHAT_AGENT_CARD_SHELL).toContain('border-outline-variant/30');
    expect(CHAT_AGENT_CARD_SHELL).toContain('bg-white');
    expect(CHAT_AGENT_CARD_SHELL).not.toMatch(/\bmt-|\bmb-/);
  });
});

describe('shouldPinLiveTodos', () => {
  it('pins incomplete todos while running', () => {
    expect(
      shouldPinLiveTodos(sampleTodos, { isRunning: true, awaitingHuman: false }),
    ).toBe(true);
  });

  it('pins incomplete todos while awaiting human', () => {
    expect(
      shouldPinLiveTodos(sampleTodos, { isRunning: false, awaitingHuman: true }),
    ).toBe(true);
  });

  it('does not pin when idle and not awaiting', () => {
    expect(
      shouldPinLiveTodos(sampleTodos, { isRunning: false, awaitingHuman: false }),
    ).toBe(false);
  });

  it('does not pin an empty list', () => {
    expect(shouldPinLiveTodos([], { isRunning: true, awaitingHuman: false })).toBe(false);
  });

  it('keeps pinning completed todos while the turn is still running', () => {
    expect(
      shouldPinLiveTodos(
        [item('completed', 'a'), item('completed', 'b')],
        { isRunning: true, awaitingHuman: false },
      ),
    ).toBe(true);
  });

  it('unpins when every todo is completed and the turn is idle', () => {
    expect(
      shouldPinLiveTodos(
        [item('completed', 'a'), item('completed', 'b')],
        { isRunning: false, awaitingHuman: false },
      ),
    ).toBe(false);
  });
});

describe('TodoCardView collapse / expand markup', () => {
  it('renders nothing for an empty list', () => {
    expect(renderToStaticMarkup(React.createElement(TodoCardView, { todos: [], t }))).toBe('');
  });

  it('defaults to expanded with list + progress', () => {
    const html = renderToStaticMarkup(
      React.createElement(TodoCardView, { todos: sampleTodos, t, pinned: true }),
    );
    expect(html).toContain('data-testid="todo-card"');
    expect(html).toContain('data-pinned="true"');
    expect(html).toContain('data-expanded="true"');
    expect(html).toContain('data-testid="todo-card-list"');
    expect(html).toContain('1/3');
    expect(html).toContain('Ship D20');
    expect(html).toContain('aria-expanded="true"');
    expect(html).toContain('Collapse Todos');
  });

  it('hides the list when controlled collapsed', () => {
    const html = renderToStaticMarkup(
      React.createElement(TodoCardView, {
        todos: sampleTodos,
        t,
        pinned: true,
        expanded: false,
      }),
    );
    expect(html).toContain('data-expanded="false"');
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain('Expand Todos');
    expect(html).toContain('1/3');
    expect(html).not.toContain('data-testid="todo-card-list"');
    expect(html).not.toContain('Ship D20');
  });

  it('shows the list when controlled expanded', () => {
    const html = renderToStaticMarkup(
      React.createElement(TodoCardView, {
        todos: sampleTodos,
        t,
        live: true,
        expanded: true,
      }),
    );
    expect(html).toContain('data-live="true"');
    expect(html).toContain('data-expanded="true"');
    expect(html).toContain('data-testid="todo-card-list"');
    expect(html).toContain('Ship D19');
  });

  it('wires the header toggle to onExpandedChange', () => {
    const onExpandedChange = vi.fn();
    const html = renderToStaticMarkup(
      React.createElement(TodoCardView, {
        todos: sampleTodos,
        t,
        expanded: true,
        onExpandedChange,
      }),
    );
    // Static markup cannot click; assert disclosure control is present for hosts/E2E.
    expect(html).toContain('data-testid="chat-agent-card-toggle"');
    expect(html).toContain('type="button"');
    expect(onExpandedChange).not.toHaveBeenCalled();
  });
});
