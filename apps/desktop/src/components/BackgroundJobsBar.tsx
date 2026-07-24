/**
 * D11 — background shell job chips above the Chat composer.
 */
import React, { useState } from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import type { BackgroundJob } from '../types';
import { ChatAgentCardStatus, type ChatCardStatusTone } from './chatAgentCard';

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

function BackgroundJobChip({
  job,
  t,
  onKill,
}: {
  job: BackgroundJob;
  t: (key: string) => string;
  onKill: (jobId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const canKill = job.status === 'running';
  return (
    <div
      data-testid={`bg-job-${job.id}`}
      className="flex flex-col gap-1 rounded-lg border border-outline-variant/50 bg-surface-container-low/60 px-2.5 py-2 min-w-[200px] max-w-[360px]"
    >
      <div className="flex items-start gap-2 min-w-0">
        <LegacyIcon
          name="terminal"
          className="text-[15px] text-on-surface-variant/70 mt-0.5 shrink-0"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[12px] font-semibold text-on-surface truncate">
              {job.title || job.command}
            </span>
            <ChatAgentCardStatus tone={statusTone(job.status)}>
              {statusLabel(job.status, t)}
            </ChatAgentCardStatus>
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <button
              type="button"
              className="text-[10px] font-semibold text-primary hover:underline"
              onClick={() => setOpen((v) => !v)}
            >
              {open ? t('Hide output') : t('View output')}
            </button>
            {canKill ? (
              <button
                type="button"
                className="text-[10px] font-semibold text-rose-600 hover:underline"
                onClick={() => onKill(job.id)}
              >
                {t('Kill')}
              </button>
            ) : null}
          </div>
          {open ? (
            <pre className="mt-1.5 max-h-40 overflow-auto rounded-md bg-surface-container-high/50 p-2 text-[10px] leading-snug text-on-surface-variant whitespace-pre-wrap break-words">
              {job.output?.trim() || t('(no output yet)')}
            </pre>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function BackgroundJobsBar({
  jobs,
  t,
  onKillJob,
}: {
  jobs: BackgroundJob[];
  t: (key: string) => string;
  onKillJob: (jobId: string) => void;
}) {
  const visible = jobs.filter((job) => job.status === 'running' || job.output?.trim());
  if (visible.length === 0) return null;
  return (
    <div
      data-testid="background-jobs-bar"
      className="w-full max-w-3xl mx-auto px-3 pb-2 flex flex-wrap gap-2"
    >
      {visible.map((job) => (
        <BackgroundJobChip key={job.id} job={job} t={t} onKill={onKillJob} />
      ))}
    </div>
  );
}
