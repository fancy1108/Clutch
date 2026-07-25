/**
 * D24 — Chat diagnostics issues strip.
 */
import React from 'react';

export interface DiagnosticIssue {
  tool: string;
  path: string;
  line: string;
  message: string;
}

export function DiagnosticsIssuesStrip({
  issues,
  t,
}: {
  issues: DiagnosticIssue[];
  t: (key: string) => string;
}) {
  if (!issues.length) return null;
  return (
    <div
      data-testid="chat-diagnostics-strip"
      className="w-full max-w-3xl mx-auto px-3 pb-2"
    >
      <div className="rounded-lg border border-rose-300/60 bg-rose-50/80 px-3 py-2">
        <div className="text-[11px] font-semibold text-rose-900 mb-1">
          {t('Code diagnostics')} ({issues.length})
        </div>
        <ul className="max-h-24 overflow-y-auto space-y-0.5">
          {issues.slice(0, 12).map((item, idx) => (
            <li key={`${item.tool}-${item.path}-${idx}`} className="text-[10px] text-rose-800 truncate">
              [{item.tool}] {item.path}
              {item.line ? `:${item.line}` : ''} — {item.message}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
