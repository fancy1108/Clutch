/**
 * D30 — session overview board (all local Chat sessions + status badges).
 */
import React, { useMemo } from 'react';
import { sessionActivityAt, type SessionRecord } from '../services/runApi';
import { LegacyIcon } from './ui/LegacyIcon';

export type SessionBoardStatus = 'running' | 'done' | 'idle';

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
  if (['passed', 'done', 'completed', 'idle'].includes(session.status)) return 'done';
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
  const rows = useMemo(() => sessionBoardRows(sessions), [sessions]);
  const zh = language === 'zh';

  if (!open) return null;

  return (
    <div
      className="absolute bottom-full left-0 right-0 mb-1 z-50 animate-in fade-in slide-in-from-bottom-1 duration-150"
      data-testid="session-overview-board"
    >
      <div className="rounded-xl border border-outline-variant/40 bg-surface-bright shadow-xl overflow-hidden">
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-outline-variant/30">
          <div className="flex items-center gap-2 min-w-0">
            <LegacyIcon name="view_list" className="text-[16px] text-on-surface-variant" />
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
                  <StatusBadge status={status} language={language} />
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
