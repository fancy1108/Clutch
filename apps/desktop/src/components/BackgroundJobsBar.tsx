/**
 * D11 — background shell jobs.
 * Running: sticky above composer. Finished: sealed into Chat (`msg.bgJob`).
 * Chrome aligns with `chatAgentCard` / UI_UX_GUIDELINES §4.1 · §4.2.
 */
import React, { useState } from 'react';
import { Square, Terminal } from 'lucide-react';
import type { BackgroundJob } from '../types';
import {
  CHAT_AGENT_CARD,
  CHAT_AGENT_CARD_SHELL,
  ChatAgentCardStatus,
  type ChatCardStatusTone,
} from './chatAgentCard';

function statusTone(status: BackgroundJob['status']): ChatCardStatusTone {
  if (status === 'done') return 'success';
  if (status === 'failed' || status === 'killed') return 'danger';
  return 'pending';
}

function statusLabel(status: BackgroundJob['status'], t: (key: string) => string): string {
  if (status === 'done') return t('Done');
  if (status === 'failed') return t('Failed');
  if (status === 'killed') return t('Killed');
  return t('Running');
}

export function BackgroundJobChip({
  job,
  t,
  onKill,
  variant = 'dock',
}: {
  job: BackgroundJob;
  t: (key: string) => string;
  onKill?: (jobId: string) => void;
  /** `dock` = compact composer strip; `feed` = in-timeline card under Supervisor. */
  variant?: 'dock' | 'feed';
}) {
  const [open, setOpen] = useState(variant === 'feed' && job.status !== 'running');
  const [killing, setKilling] = useState(false);
  const canKill = job.status === 'running' && typeof onKill === 'function' && !killing;
  const shell = variant === 'feed' ? CHAT_AGENT_CARD : CHAT_AGENT_CARD_SHELL;
  const tone = killing && job.status === 'running' ? 'danger' : statusTone(job.status);
  const label =
    killing && job.status === 'running' ? t('Stopping') : statusLabel(job.status, t);
  return (
    <div
      data-testid={`bg-job-${job.id}`}
      className={`${shell} w-full`}
    >
      <div className="flex items-center gap-2 px-2.5 py-1.5 bg-surface-container-low">
        <Terminal className="h-3.5 w-3.5 text-on-surface-variant/70 shrink-0" strokeWidth={2} aria-hidden />
        <span
          className="text-[12px] font-semibold text-on-surface font-mono truncate min-w-0 flex-1"
          title={job.command}
        >
          {job.title || job.command}
        </span>
        <ChatAgentCardStatus tone={tone}>{label}</ChatAgentCardStatus>
      </div>

      <div className="px-2.5 py-1.5 flex flex-wrap items-center gap-2 border-t border-outline-variant/20">
        <button
          type="button"
          className="rounded-md border border-outline-variant/40 bg-white px-2 py-1 text-[10px] font-semibold text-on-surface hover:bg-surface-container transition-colors"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? t('Hide output') : t('View output')}
        </button>
        {canKill ? (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-[10px] font-semibold text-rose-800 hover:bg-rose-600 hover:text-white transition-all"
            onClick={() => {
              setKilling(true);
              onKill?.(job.id);
            }}
          >
            <Square className="h-2.5 w-2.5 fill-current" aria-hidden />
            {t('Kill')}
          </button>
        ) : null}
        {killing && job.status === 'running' ? (
          <span className="text-[10px] font-semibold text-rose-700">{t('Stopping')}…</span>
        ) : null}
      </div>
      {open ? (
        <pre className="mx-2.5 mb-2 max-h-32 overflow-auto rounded-lg border border-outline-variant/25 bg-surface-container-low p-2 text-[11px] leading-relaxed font-mono text-on-surface-variant whitespace-pre-wrap break-words">
          {job.output?.trim() || t('(no output yet)')}
        </pre>
      ) : null}
    </div>
  );
}

/** Sticky composer strip — running jobs only (finished move into Chat). */
export function BackgroundJobsBar({
  jobs,
  t,
  onKillJob,
}: {
  jobs: BackgroundJob[];
  t: (key: string) => string;
  onKillJob: (jobId: string) => void;
}) {
  const running = jobs.filter((job) => job.status === 'running');
  if (running.length === 0) return null;
  return (
    <div
      data-testid="background-jobs-bar"
      className="w-full max-w-3xl mx-auto px-3 pb-2"
    >
      <div className="rounded-xl border border-outline-variant/30 bg-white shadow-sm px-2.5 py-2 space-y-1.5">
        <p className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/70 px-0.5">
          {t('Background jobs')}
        </p>
        <div className="flex flex-col gap-1.5">
          {running.map((job) => (
            <BackgroundJobChip key={job.id} job={job} t={t} onKill={onKillJob} variant="dock" />
          ))}
        </div>
      </div>
    </div>
  );
}
