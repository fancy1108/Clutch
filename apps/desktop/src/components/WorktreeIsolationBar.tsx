/**
 * D32 — worktree isolation status (active only).
 * Idle enable lives in ChatInputBar toolbar (progressive disclosure).
 */
import React from 'react';
import { LegacyIcon } from './ui/LegacyIcon';

export interface WorktreeIsolationState {
  id: string;
  path: string;
  branch: string;
  enabled: boolean;
  dirty?: boolean;
}

export function WorktreeIsolationBar({
  worktree,
  t,
  onMerge,
  onDiscard,
}: {
  worktree: WorktreeIsolationState | null;
  t: (key: string) => string;
  onMerge: () => void;
  onDiscard: () => void;
}) {
  if (!worktree?.enabled) return null;

  return (
    <div
      data-testid="worktree-isolation-bar"
      className="w-full max-w-3xl mx-auto px-3 pb-1.5"
    >
      <div
        className="flex items-center gap-2 rounded-xl border border-sky-500/35 bg-sky-500/[0.06] px-2.5 py-1.5"
        data-testid="worktree-active-chip"
      >
        <LegacyIcon name="git-branch" className="text-[14px] text-sky-700 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-semibold text-on-surface truncate">
            {worktree.branch}
            {worktree.dirty ? ` · ${t('dirty')}` : ''}
          </div>
          <div className="text-[10px] text-on-surface-variant/70 truncate">{worktree.path}</div>
        </div>
        <button
          type="button"
          data-testid="merge-worktree"
          className="shrink-0 rounded-md bg-primary px-2 py-0.5 text-[10px] font-semibold text-on-primary hover:bg-primary/90"
          onClick={onMerge}
        >
          {t('Merge')}
        </button>
        <button
          type="button"
          data-testid="discard-worktree"
          className="shrink-0 rounded-md border border-rose-300 px-2 py-0.5 text-[10px] font-semibold text-rose-700 hover:bg-rose-50"
          onClick={onDiscard}
        >
          {t('Discard')}
        </button>
      </div>
    </div>
  );
}
