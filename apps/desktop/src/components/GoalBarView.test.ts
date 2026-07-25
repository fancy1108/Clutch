import { describe, expect, it } from 'vitest';
import { shouldShowGoalBar } from './GoalBarView';

describe('GoalBarView', () => {
  it('shows bar for active goals only', () => {
    expect(shouldShowGoalBar({ title: '修登录', progress: 20, done: false })).toBe(true);
    expect(shouldShowGoalBar({ title: '修登录', progress: 100, done: true })).toBe(false);
    expect(shouldShowGoalBar(undefined)).toBe(false);
  });
});
