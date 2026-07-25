/** D29 — session goal bar (from goal_write / agent_goal). */
import React from 'react';
import { Check, Target } from 'lucide-react';
import type { AgentGoal } from '../types';

export function shouldShowGoalBar(goal: AgentGoal | null | undefined): boolean {
  return Boolean(goal?.title?.trim()) && !goal?.done;
}

export function GoalBarView({
  goal,
  t,
}: {
  goal: AgentGoal;
  t: (key: string) => string;
}) {
  const progress = Math.max(0, Math.min(100, goal.progress ?? 0));
  return (
    <div
      data-testid="goal-bar"
      className="rounded-xl border border-outline-variant/35 bg-surface-container-low px-3 py-2 shadow-sm"
    >
      <div className="flex items-center gap-2 min-w-0">
        {goal.done ? (
          <Check className="h-4 w-4 shrink-0 text-green-600" strokeWidth={2.5} aria-hidden />
        ) : (
          <Target className="h-4 w-4 shrink-0 text-primary" strokeWidth={2} aria-hidden />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-[12px] font-semibold text-on-surface">
              {goal.title}
            </span>
            <span className="shrink-0 text-[10px] font-mono text-on-surface-variant/70">
              {goal.done ? t('Done') : `${progress}%`}
            </span>
          </div>
          {!goal.done ? (
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-container-high">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
