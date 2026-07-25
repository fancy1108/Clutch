/**
 * D22 — usage history panel (current run + prior sessions).
 */
import React, { useMemo } from 'react';
import type { SessionRecord } from '../services/runApi';
import { LegacyIcon } from './ui/LegacyIcon';

export interface UsageDashboardProps {
  open: boolean;
  onClose: () => void;
  currentRunId?: string;
  sessions: SessionRecord[];
  runStats?: {
    tool_steps?: number;
    max_steps?: number;
    session_tokens?: number;
  };
  sessionTokens?: number;
  language: 'en' | 'zh';
}

function formatSessionDate(value: string | undefined, language: 'en' | 'zh'): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toLocaleString(language === 'zh' ? 'zh-CN' : undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function usageRowsFromSessions(
  sessions: SessionRecord[],
  currentRunId?: string,
): SessionRecord[] {
  const seen = new Set<string>();
  const rows: SessionRecord[] = [];
  for (const session of sessions) {
    const id = session.run_id;
    if (!id || seen.has(id)) continue;
    seen.add(id);
    rows.push(session);
  }
  rows.sort((a, b) => String(b.started_at || '').localeCompare(String(a.started_at || '')));
  if (currentRunId) {
    const idx = rows.findIndex((row) => row.run_id === currentRunId);
    if (idx > 0) {
      const [current] = rows.splice(idx, 1);
      rows.unshift(current);
    }
  }
  return rows.slice(0, 12);
}

export function UsageDashboard({
  open,
  onClose,
  currentRunId,
  sessions,
  runStats,
  sessionTokens,
  language,
}: UsageDashboardProps) {
  const rows = useMemo(
    () => usageRowsFromSessions(sessions, currentRunId),
    [sessions, currentRunId],
  );
  const currentSteps = runStats?.tool_steps ?? 0;
  const currentTokens = runStats?.session_tokens ?? sessionTokens ?? 0;
  const zh = language === 'zh';

  if (!open) return null;

  return (
    <div
      className="absolute bottom-full left-0 right-0 mb-1 mx-0 z-50 animate-in fade-in slide-in-from-bottom-1 duration-150"
      data-testid="usage-dashboard"
    >
      <div className="rounded-xl border border-outline-variant bg-white shadow-xl overflow-hidden">
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-outline-variant/40 bg-surface-container-low/40">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold text-on-surface">
              {zh ? '用量看板' : 'Usage dashboard'}
            </p>
            <p className="text-[10px] text-on-surface-variant/70 font-mono truncate">
              {zh ? '本局' : 'This run'}: {currentSteps} {zh ? '步' : 'steps'} · ~
              {currentTokens.toLocaleString()} {zh ? 'token' : 'tok'}
            </p>
          </div>
          <button
            type="button"
            aria-label={zh ? '关闭' : 'Close'}
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg text-on-surface-variant/60 hover:bg-surface-container-low"
          >
            <LegacyIcon name="close" className="text-[16px]" />
          </button>
        </div>
        <div className="max-h-48 overflow-y-auto">
          {rows.length === 0 ? (
            <p className="px-3 py-4 text-[11px] text-on-surface-variant/60 italic">
              {zh ? '暂无历史会话' : 'No session history yet'}
            </p>
          ) : (
            <table className="w-full text-left text-[10.5px]">
              <thead className="sticky top-0 bg-white/95 backdrop-blur-sm text-on-surface-variant/70">
                <tr>
                  <th className="px-3 py-1.5 font-semibold">{zh ? '会话' : 'Session'}</th>
                  <th className="px-2 py-1.5 font-semibold text-right">{zh ? '步' : 'Steps'}</th>
                  <th className="px-3 py-1.5 font-semibold text-right">~tok</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const isCurrent = row.run_id === currentRunId;
                  const steps = isCurrent ? currentSteps : (row.tool_steps ?? 0);
                  const tokens = isCurrent ? currentTokens : (row.session_tokens ?? 0);
                  return (
                    <tr
                      key={row.run_id}
                      data-testid={`usage-row-${row.run_id}`}
                      className={
                        isCurrent
                          ? 'bg-primary/5 text-on-surface'
                          : 'text-on-surface-variant border-t border-outline-variant/20'
                      }
                    >
                      <td className="px-3 py-1.5 min-w-0">
                        <div className="truncate font-medium text-[11px]">
                          {row.title || row.run_id.slice(0, 12)}
                        </div>
                        <div className="text-[9.5px] text-on-surface-variant/60">
                          {formatSessionDate(row.started_at, language)}
                        </div>
                      </td>
                      <td className="px-2 py-1.5 text-right font-mono">{steps}</td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        {tokens.toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
