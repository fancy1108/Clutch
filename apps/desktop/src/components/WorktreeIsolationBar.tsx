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

/** FM-11 spawn/list bar: idle Chat must not show a dangling Add button. */
export function worktreeBarVisible(
  worktree: WorktreeIsolationState | null,
  extras: WorktreeIsolationState[],
  error: string | null,
): boolean {
  return Boolean(worktree?.enabled) || extras.length > 0 || Boolean(error);
}

export function canAddParallelWorktree(worktree: WorktreeIsolationState | null): boolean {
  return Boolean(worktree?.enabled);
}

export function spawnErrorFromBody(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object' || !('detail' in body)) return fallback;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (detail && typeof detail === 'object' && 'message' in detail) {
    const msg = (detail as { message: unknown }).message;
    if (typeof msg === 'string' && msg.trim()) return msg;
  }
  return fallback;
}

async function spawnErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    return spawnErrorFromBody(await res.json(), fallback);
  } catch {
    return fallback;
  }
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

  const showSpawn = canAddParallelWorktree(worktree);
  if (!worktreeBarVisible(worktree, extras, error)) return null;

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
      {showSpawn || error ? (
        <div className="flex items-center gap-2">
          {showSpawn ? (
            <button
              type="button"
              data-testid="add-parallel-worktree"
              className={`${BTN_SECONDARY} px-2 py-1 text-[10px] font-semibold`}
              onClick={() => {
                setError(null);
                void sidecarFetch(`${BASE}/api/worktree/spawn`, { method: 'POST' })
                  .then(async (res) => {
                    if (!res.ok) throw new Error(await spawnErrorMessage(res, t('Failed')));
                    return reload();
                  })
                  .catch((err: unknown) => {
                    setError(err instanceof Error ? err.message : t('Failed'));
                  });
              }}
            >
              {t('Add parallel worktree')}
            </button>
          ) : null}
          {error ? <span className="text-[10px] text-rose-700">{error}</span> : null}
        </div>
      ) : null}
    </div>
  );
}
