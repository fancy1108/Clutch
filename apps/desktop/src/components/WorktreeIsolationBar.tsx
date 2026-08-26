/**
 * D32 — worktree isolation status (active only).
 * Idle enable lives in ChatInputBar toolbar (progressive disclosure).
 * FM-11 — extra parallel trees listed from disk with merge/discard.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import { SIDECAR_BASE as BASE, sidecarFetch } from '../services/sidecarUrl';
import { BTN_SECONDARY } from './ui/buttonStyles';

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
  const [extras, setExtras] = useState<WorktreeIsolationState[]>([]);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const res = await sidecarFetch(`${BASE}/api/worktree`);
    if (!res.ok) return;
    const body = (await res.json()) as { worktrees?: WorktreeIsolationState[] };
    const primaryId = worktree?.id;
    setExtras((body.worktrees ?? []).filter((item) => item.id !== primaryId));
  }, [worktree?.id]);

  useEffect(() => {
    void reload().catch(() => setExtras([]));
  }, [reload, worktree?.id]);

  return (
    <div data-testid="worktree-isolation-bar" className="w-full max-w-3xl mx-auto px-3 pb-1.5 space-y-1.5">
      {worktree?.enabled ? (
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
      ) : null}
      {extras.map((item) => (
        <div
          key={item.id}
          data-testid={`parallel-worktree-${item.id}`}
          className="flex items-center gap-2 rounded-xl border border-outline-variant/40 bg-surface-container-low px-2.5 py-1.5"
        >
          <div className="flex-1 min-w-0">
            <div className="text-[11px] font-semibold truncate">{item.branch}</div>
            <div className="text-[10px] text-on-surface-variant/70 truncate">{item.path}</div>
          </div>
          <button
            type="button"
            className="text-[10px] font-semibold text-primary"
            onClick={() => {
              void sidecarFetch(`${BASE}/api/worktree/${encodeURIComponent(item.id)}/merge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ run_id: '' }),
              }).then(() => reload());
            }}
          >
            {t('Merge')}
          </button>
          <button
            type="button"
            className="text-[10px] font-semibold text-rose-700"
            onClick={() => {
              void sidecarFetch(`${BASE}/api/worktree/${encodeURIComponent(item.id)}/discard`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ run_id: '' }),
              }).then(() => reload());
            }}
          >
            {t('Discard')}
          </button>
        </div>
      ))}
      <div className="flex items-center gap-2">
        <button
          type="button"
          data-testid="add-parallel-worktree"
          className={`${BTN_SECONDARY} px-2 py-1 text-[10px] font-semibold`}
          onClick={() => {
            setError(null);
            void sidecarFetch(`${BASE}/api/worktree/spawn`, { method: 'POST' })
              .then((res) => {
                if (!res.ok) throw new Error('spawn failed');
                return reload();
              })
              .catch((err: unknown) => {
                setError(err instanceof Error ? err.message : t('Failed'));
              });
          }}
        >
          {t('Add parallel worktree')}
        </button>
        {error ? <span className="text-[10px] text-rose-700">{error}</span> : null}
      </div>
    </div>
  );
}
