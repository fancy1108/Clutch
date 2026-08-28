/**
 * D32 / FM-11 — worktree switcher lives in the footer next to Branch.
 * Composer + still exposes Enable (progressive disclosure). No extra sky chip.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import { FooterFieldChevron, FooterFieldLabel, FooterFieldValue, FooterMenuItem, FooterMenuPanel, FooterMenuRowIcon, FOOTER_CHIP_BUTTON_CLASS, footerIdleHiddenClass } from './FooterMenu';
import { SIDECAR_BASE as BASE, sidecarFetch } from '../services/sidecarUrl';

export interface WorktreeIsolationState {
  id: string;
  path: string;
  branch: string;
  enabled: boolean;
  dirty?: boolean;
}

export function footerWorktreeLabel(worktree: WorktreeIsolationState | null): string {
  if (worktree?.enabled && (worktree.branch || worktree.id)) {
    return worktree.branch || worktree.id;
  }
  return '—';
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

export function FooterWorktreeMenu({
  worktree,
  open,
  t,
  onToggle,
  onSelectMain,
  onSelectWorktree,
  onEnable,
  onMerge,
  onDiscard,
}: {
  worktree: WorktreeIsolationState | null;
  open: boolean;
  t: (key: string) => string;
  onToggle: () => void;
  onSelectMain: () => void;
  onSelectWorktree: (id: string) => void;
  onEnable: () => void;
  onMerge: (wtId: string) => void;
  onDiscard: (wtId: string) => void;
}) {
  const [trees, setTrees] = useState<WorktreeIsolationState[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [spawning, setSpawning] = useState(false);
  const active = Boolean(worktree?.enabled);
  const label = footerWorktreeLabel(worktree);
  const rows =
    worktree?.enabled && !trees.some((item) => item.id === worktree.id)
      ? [worktree, ...trees]
      : trees;

  const reload = useCallback(async () => {
    const res = await sidecarFetch(`${BASE}/api/worktree`);
    if (!res.ok) return;
    const body = (await res.json()) as { worktrees?: WorktreeIsolationState[] };
    setTrees(body.worktrees ?? []);
  }, []);

  useEffect(() => {
    if (!open) return;
    setError(null);
    void reload().catch(() => setTrees([]));
  }, [open, reload, worktree?.id]);

  const spawnParallel = () => {
    if (spawning) return;
    setError(null);
    setSpawning(true);
    void sidecarFetch(`${BASE}/api/worktree/spawn`, { method: 'POST' })
      .then(async (res) => {
        if (!res.ok) throw new Error(await spawnErrorMessage(res, t('Failed')));
        return reload();
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : t('Failed'));
      })
      .finally(() => {
        setSpawning(false);
      });
  };

  return (
    <div
      className={`relative min-w-0 ${footerIdleHiddenClass(!active)}`}
      data-testid={active ? 'worktree-active-chip' : undefined}
    >
      <button
        type="button"
        data-testid="footer-worktree-trigger"
        data-active={active ? 'true' : 'false'}
        onClick={onToggle}
        className={`${FOOTER_CHIP_BUTTON_CLASS} text-on-surface-variant`}
        aria-label={`${t('Worktree')}: ${label}`}
        title={`${t('Worktree')}: ${label}`}
      >
        <LegacyIcon name="folder-git" className="text-[15px] text-on-surface-variant shrink-0" />
        <FooterFieldLabel>{t('Worktree')}</FooterFieldLabel>
        <FooterFieldValue title={label}>{label}</FooterFieldValue>
        <FooterFieldChevron />
      </button>
      {open ? (
        <FooterMenuPanel testId="footer-worktree-menu">
          <FooterMenuItem
            testId="footer-worktree-main"
            selected={!active}
            onClick={onSelectMain}
          >
            {t('Main workspace')}
          </FooterMenuItem>
          {rows.map((item) => {
            const selected = active && item.id === worktree?.id;
            return (
            <FooterMenuItem
              key={item.id}
              testId={`parallel-worktree-${item.id}`}
              selected={selected}
              onClick={() => onSelectWorktree(item.id)}
              actions={
                <>
                  <FooterMenuRowIcon
                    name="git-merge"
                    label={t('Merge')}
                    testId={selected ? 'merge-worktree' : `merge-worktree-${item.id}`}
                    onClick={() => onMerge(item.id)}
                  />
                  <FooterMenuRowIcon
                    name="delete"
                    label={t('Discard')}
                    danger
                    testId={selected ? 'discard-worktree' : `discard-worktree-${item.id}`}
                    onClick={() => onDiscard(item.id)}
                  />
                </>
              }
            >
              {item.branch}
              {item.dirty ? ` · ${t('dirty')}` : ''}
            </FooterMenuItem>
            );
          })}
          <button
            type="button"
            data-testid={
              !active && !trees.length ? 'footer-worktree-enable' : 'add-parallel-worktree'
            }
            disabled={spawning}
            aria-busy={spawning}
            onClick={!active && !trees.length ? onEnable : spawnParallel}
            className="w-full flex items-center gap-2 px-3 py-2 text-[11px] text-on-surface-variant hover:bg-surface-container-low border-t border-outline-variant/40 text-left disabled:opacity-70 disabled:pointer-events-none"
          >
            <LegacyIcon
              name={spawning ? 'progress_activity' : 'add'}
              className="text-[14px] w-4 flex-shrink-0"
            />
            <span>
              {spawning
                ? t('Creating worktree…')
                : !active && !trees.length
                  ? t('Enable worktree')
                  : t('Add parallel worktree')}
            </span>
          </button>
          {error ? (
            <p className="px-3 py-2 pl-9 text-[11px] text-on-surface-variant">{error}</p>
          ) : null}
        </FooterMenuPanel>
      ) : null}
    </div>
  );
}
