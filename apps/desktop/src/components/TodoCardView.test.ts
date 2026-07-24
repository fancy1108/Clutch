import { describe, expect, it } from 'vitest';
import { todosAreComplete } from './TodoCardView';
import type { TodoItem } from '../types';

const item = (status: TodoItem['status'], id = status): TodoItem => ({
  id,
  content: id,
  status,
});

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
