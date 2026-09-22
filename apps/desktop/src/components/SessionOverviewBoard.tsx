/**
 * D30 — session overview board (all local Chat sessions + status badges).
 */
import React, { useMemo, useState } from 'react';
import { sessionActivityAt, type SessionRecord } from '../services/runApi';
import { LegacyIcon } from './ui/LegacyIcon';

export type SessionBoardStatus = 'running' | 'done' | 'waiting' | 'failed' | 'idle';
export type SessionBoardFilter = 'all' | SessionBoardStatus;
export type SessionBoardSummary = Record<SessionBoardStatus, number>;

export function resolveSessionBoardStatus(
  session: SessionRecord,
  currentRunId: string | undefined,
  clutchStatus: string | undefined,
): SessionBoardStatus {
  const isActive = Boolean(currentRunId && session.run_id === currentRunId);
  const activeBusy =
    isActive &&
    (clutchStatus === 'running' ||
      clutchStatus === 'awaiting_human' ||
      clutchStatus === 'refining');
  if (activeBusy || session.status === 'running') return 'running';
  if (['waiting_approval', 'awaiting_human', 'awaiting_user', 'blocked', 'paused'].includes(session.status)) {
    return 'waiting';
  }
  if (['failed', 'error', 'cancelled', 'rejected'].includes(session.status)) return 'failed';
  if (['passed', 'done', 'completed'].includes(session.status)) return 'done';
  if (['queued', 'pending'].includes(session.status)) return 'idle';
  return 'idle';
}

export function sessionBoardRows(sessions: SessionRecord[]): SessionRecord[] {
  const seen = new Set<string>();
  const rows: SessionRecord[] = [];
  for (const session of sessions) {
    if (!session.run_id || seen.has(session.run_id)) continue;
    seen.add(session.run_id);
    rows.push(session);
  }
  return rows.sort((a, b) => sessionActivityAt(b).localeCompare(sessionActivityAt(a)));
}

export function getSessionBoardReviewTarget(
  sessions: SessionRecord[],
  currentRunId?: string,
  clutchStatus?: string,
): SessionRecord | undefined {
  const waiting = sessionBoardRows(sessions).filter(
    (session) => resolveSessionBoardStatus(session, currentRunId, clutchStatus) === 'waiting',
  );
  return waiting[0];
}

export function filterSessionBoardRows(
  sessions: SessionRecord[],
  filter: SessionBoardFilter,
  currentRunId?: string,
  clutchStatus?: string,
): SessionRecord[] {
  const rows = sessionBoardRows(sessions);
  if (filter === 'all') return rows;
  return rows.filter((session) => resolveSessionBoardStatus(session, currentRunId, clutchStatus) === filter);
}

export function summarizeSessionBoardStatus(
  sessions: SessionRecord[],
  currentRunId?: string,
  clutchStatus?: string,
): SessionBoardSummary {
  const summary: SessionBoardSummary = {
    running: 0,
    done: 0,
    waiting: 0,
    failed: 0,
    idle: 0,
  };

  for (const session of sessionBoardRows(sessions)) {
    summary[resolveSessionBoardStatus(session, currentRunId, clutchStatus)] += 1;
  }
  return summary;
}

export function getSessionBoardActionLabel(
  status: SessionBoardStatus,
  language: 'en' | 'zh',
): string {
  const zh = language === 'zh';
  switch (status) {
    case 'running':
      return zh ? '跟踪' : 'Follow';
    case 'waiting':
      return zh ? '处理' : 'Review';
    case 'failed':
      return zh ? '检查' : 'Inspect';
    case 'done':
      return zh ? '查看' : 'Open';
    default:
      return zh ? '查看' : 'View';
  }
}

function StatusBadge({
  status,
  language,
}: {
  status: SessionBoardStatus;
  language: 'en' | 'zh';
}) {
  const zh = language === 'zh';
  if (status === 'running') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
        <LegacyIcon name="progress_activity" className="text-[11px] animate-spin" aria-hidden />
        {zh ? '进行中' : 'Running'}
      </span>
    );
  }
  if (status === 'waiting') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
        <LegacyIcon name="schedule" className="text-[11px]" aria-hidden />
        {zh ? '待审批' : 'Waiting'}
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-700">
        <LegacyIcon name="error" className="text-[11px]" aria-hidden />
        {zh ? '失败' : 'Failed'}
      </span>
    );
  }
  if (status === 'done') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
        <LegacyIcon name="check_circle" className="text-[11px]" aria-hidden />
        {zh ? '已完成' : 'Done'}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-surface-container-high px-2 py-0.5 text-[10px] font-medium text-on-surface-variant/70">
      {zh ? '空闲' : 'Idle'}
    </span>
  );
}

export interface SessionOverviewBoardProps {
  open: boolean;
  onClose: () => void;
  sessions: SessionRecord[];
  currentRunId?: string;
  clutchStatus?: string;
  language: 'en' | 'zh';
  onSelectSession?: (session: SessionRecord) => void;
}

export function SessionOverviewBoard({
  open,
  onClose,
  sessions,
  currentRunId,
  clutchStatus,
  language,
  onSelectSession,
}: SessionOverviewBoardProps) {
  const [filter, setFilter] = useState<SessionBoardFilter>('all');
  const rows = useMemo(
    () => filterSessionBoardRows(sessions, filter, currentRunId, clutchStatus),
    [sessions, filter, currentRunId, clutchStatus],
  );
  const summary = useMemo(
    () => summarizeSessionBoardStatus(sessions, currentRunId, clutchStatus),
    [sessions, currentRunId, clutchStatus],
  );
  const reviewTarget = useMemo(
    () => getSessionBoardReviewTarget(sessions, currentRunId, clutchStatus),
    [sessions, currentRunId, clutchStatus],
  );
  const zh = language === 'zh';
  const filterOptions: { value: SessionBoardFilter; label: string }[] = [
    { value: 'all', label: zh ? '全部' : 'All' },
    { value: 'running', label: zh ? '进行中' : 'Running' },
    { value: 'waiting', label: zh ? '待审批' : 'Waiting' },
    { value: 'failed', label: zh ? '失败' : 'Failed' },
    { value: 'done', label: zh ? '已完成' : 'Done' },
  ];
  const summaryOptions: Array<{ key: SessionBoardStatus; label: string }> = [
    { key: 'running', label: zh ? '进行中' : 'Running' },
    { key: 'waiting', label: zh ? '待审批' : 'Waiting' },
    { key: 'failed', label: zh ? '失败' : 'Failed' },
    { key: 'done', label: zh ? '已完成' : 'Done' },
    { key: 'idle', label: zh ? '空闲' : 'Idle' },
  ];

  if (!open) return null;

  return (
    <div
      className="absolute bottom-full left-0 right-0 mb-1 z-50 animate-in fade-in slide-in-from-bottom-1 duration-150"
      data-testid="session-overview-board"
    >
      <div className="rounded-xl border border-outline-variant/40 bg-surface-bright shadow-xl overflow-hidden">
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-outline-variant/30">
          <div className="flex items-center gap-2 min-w-0">
            <LegacyIcon name="clipboard_list" className="text-[16px] text-on-surface-variant" />
            <span className="text-[11px] font-semibold text-on-surface">
              {zh ? '会话总览' : 'Session overview'}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface"
            aria-label={zh ? '关闭' : 'Close'}
          >
            <LegacyIcon name="close" className="text-[16px]" />
          </button>
        </div>
        <div className="flex flex-wrap gap-1.5 px-2 py-2 border-b border-outline-variant/30">
          {filterOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setFilter(option.value)}
              className={`rounded-full px-2 py-1 text-[10px] font-medium transition-colors ${
                filter === option.value
                  ? 'bg-primary text-white'
                  : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {reviewTarget ? (
          <div className="flex items-center justify-between gap-2 border-b border-amber-200/80 bg-amber-50/70 px-2.5 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <LegacyIcon name="warning_amber" className="text-[14px] text-amber-700" />
              <div className="min-w-0">
                <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-800/80">
                  {zh ? '待处理' : 'Needs review'}
                </div>
                <div className="truncate text-[11px] text-amber-900">
                  {summary.waiting > 1
                    ? (zh ? `${summary.waiting} 个待审批任务` : `${summary.waiting} sessions waiting for review`)
                    : (zh ? '1 个待审批任务' : '1 session waiting for review')}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                onSelectSession?.(reviewTarget);
                onClose();
              }}
              className="shrink-0 rounded-full border border-amber-300 bg-white px-2 py-1 text-[10px] font-semibold text-amber-900 hover:bg-amber-100"
            >
              {zh ? '立即处理' : getSessionBoardActionLabel('waiting', 'en')}
            </button>
          </div>
        ) : null}
        <div className="grid grid-cols-5 gap-1.5 px-2 py-2 border-b border-outline-variant/30">
          {summaryOptions.map(({ key, label }) => (
            <div
              key={key}
              className={`rounded-lg border px-2 py-1.5 text-center ${
                key === 'waiting'
                  ? 'border-amber-300/60 bg-amber-500/5'
                  : key === 'failed'
                    ? 'border-red-300/60 bg-red-500/5'
                    : key === 'running'
                      ? 'border-primary/40 bg-primary/5'
                      : 'border-outline-variant/30 bg-surface-container-low'
              }`}
            >
              <div className="text-[9px] text-on-surface-variant/70">{label}</div>
              <div className="mt-0.5 text-[12px] font-semibold text-on-surface">{summary[key]}</div>
            </div>
          ))}
        </div>
        <div className="max-h-64 overflow-y-auto">
          {rows.length === 0 ? (
            <p className="px-4 py-6 text-center text-[11px] text-on-surface-variant/60 italic">
              {zh ? '暂无会话' : 'No sessions yet'}
            </p>
          ) : (
            rows.map((session) => {
              const status = resolveSessionBoardStatus(session, currentRunId, clutchStatus);
              const isCurrent = session.run_id === currentRunId;
              return (
                <button
                  key={session.run_id}
                  type="button"
                  data-testid={`session-board-row-${session.run_id}`}
                  onClick={() => {
                    onSelectSession?.(session);
                    onClose();
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-left border-b border-outline-variant/15 last:border-b-0 transition-colors ${
                    isCurrent ? 'bg-primary/5' : 'hover:bg-surface-container-low'
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[12px] font-semibold text-on-surface">
                      {session.title?.trim() || session.run_id}
                    </div>
                    <div className="truncate text-[10px] text-on-surface-variant/60">
                      {session.parent_run_id
                        ? zh
                          ? `分支 ← ${session.parent_run_id}`
                          : `Fork ← ${session.parent_run_id}`
                        : session.workspace_name || session.workspace_id || '—'}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <StatusBadge status={status} language={language} />
                    {status !== 'idle' ? (
                      <span
                        className={`inline-flex items-center rounded-full border px-1.5 py-0.5 text-[9px] font-semibold ${
                          status === 'waiting'
                            ? 'border-amber-300 bg-amber-50 text-amber-800'
                            : status === 'failed'
                              ? 'border-red-300 bg-red-50 text-red-800'
                              : 'border-primary/30 bg-primary/5 text-primary'
                        }`}
                      >
                        {getSessionBoardActionLabel(status, language)}
                      </span>
                    ) : null}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
