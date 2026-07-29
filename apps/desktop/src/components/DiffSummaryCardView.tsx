/**
 * D6 / D50 — in-chat diff cards.
 * Inline (Cursor-style): one file per card with each edit tool step.
 * Review: multi-file summary from submit_diff_summary.
 */
import React, { useState } from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import type { DiffFileEntry, DiffLine, DiffSummary as DiffSummaryData } from '../types';
import {
  CHAT_AGENT_CARD,
  ChatAgentCardHeader,
  ChatAgentCardStatus,
} from './chatAgentCard';

function statusTone(status: string): string {
  if (status === 'A') return 'text-emerald-700';
  if (status === 'D') return 'text-rose-700';
  return 'text-amber-700';
}

function statusLabel(status: string, t: (key: string) => string): string {
  if (status === 'A') return t('Added');
  if (status === 'D') return t('Deleted');
  return t('Modified');
}

export function parsePatchToDiffs(patch: string): DiffLine[] {
  const out: DiffLine[] = [];
  let lineNum = 0;
  for (const raw of patch.split('\n')) {
    if (
      raw.startsWith('+++') ||
      raw.startsWith('---') ||
      raw.startsWith('diff ') ||
      raw.startsWith('index ')
    ) {
      continue;
    }
    if (raw.startsWith('@@')) {
      const m = /\+(\d+)/.exec(raw);
      if (m) lineNum = Math.max(0, Number(m[1]) - 1);
      continue;
    }
    if (raw.startsWith('+')) {
      lineNum += 1;
      out.push({ lineNum, type: 'addition', text: raw.slice(1) });
    } else if (raw.startsWith('-')) {
      out.push({ lineNum, type: 'deletion', text: raw.slice(1) });
    } else if (raw.startsWith('\\')) {
      continue;
    } else {
      const text = raw.startsWith(' ') ? raw.slice(1) : raw;
      lineNum += 1;
      out.push({ lineNum, type: 'normal', text });
    }
  }
  return out;
}

export function fileDiffLines(file: DiffFileEntry): DiffLine[] {
  if (file.diffs && file.diffs.length > 0) return file.diffs;
  if (file.patch?.trim()) return parsePatchToDiffs(file.patch);
  return [];
}

function countDelta(lines: DiffLine[]): { added: number; removed: number } {
  let added = 0;
  let removed = 0;
  for (const line of lines) {
    if (line.type === 'addition') added += 1;
    else if (line.type === 'deletion') removed += 1;
  }
  return { added, removed };
}

function basename(path: string): string {
  const parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
  return parts[parts.length - 1] || path;
}

export function DiffHunk({ lines }: { lines: DiffLine[] }) {
  if (lines.length === 0) {
    return (
      <p className="px-3 py-2 text-[11px] text-on-surface-variant/70 italic">No hunk preview</p>
    );
  }
  return (
    <div className="font-mono text-[11px] leading-relaxed bg-white overflow-x-auto max-h-56 overflow-y-auto border-t border-outline-variant/15">
      {lines.map((diffLine, i) => {
        let bgClass = '';
        let indicator = ' ';
        if (diffLine.type === 'addition') {
          bgClass = 'bg-emerald-50/90 text-emerald-900';
          indicator = '+';
        } else if (diffLine.type === 'deletion') {
          bgClass = 'bg-rose-50/90 text-rose-900';
          indicator = '-';
        }
        return (
          <div key={`${diffLine.lineNum}-${i}`} className={`flex ${bgClass}`}>
            <div className="w-4 shrink-0 text-center select-none opacity-60 pl-1.5">{indicator}</div>
            <pre className="flex-1 min-w-0 whitespace-pre-wrap break-all pr-2 py-0.5 m-0 font-inherit">
              {diffLine.text}
            </pre>
          </div>
        );
      })}
    </div>
  );
}

function DiffFileRow({
  file,
  t,
  onOpen,
  defaultOpen,
}: {
  file: DiffFileEntry;
  t: (key: string) => string;
  onOpen?: (path: string) => void;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const lines = fileDiffLines(file);

  return (
    <div className="border-t border-outline-variant/20 first:border-t-0">
      <div className="flex items-center gap-1.5 px-2.5 py-1.5">
        <button
          type="button"
          className="flex items-center gap-1.5 min-w-0 flex-1 text-left hover:bg-surface-container-low/80 rounded-md px-1 py-0.5"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          <LegacyIcon
            name={open ? 'expand_more' : 'chevron_right'}
            className="text-[16px] text-on-surface-variant shrink-0"
          />
          <span className={`text-[10px] font-bold w-3 text-center shrink-0 ${statusTone(file.status)}`}>
            {file.status}
          </span>
          <span className="text-[12px] font-mono text-on-surface truncate min-w-0 flex-1" title={file.path}>
            {file.path}
          </span>
          <span className="text-[9px] uppercase tracking-wider text-on-surface-variant/70 shrink-0">
            {statusLabel(file.status, t)}
          </span>
        </button>
        {onOpen ? (
          <button
            type="button"
            className="shrink-0 p-1 rounded-md text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
            title={t('Preview file')}
            aria-label={t('Preview file')}
            onClick={() => onOpen(file.path)}
          >
            <LegacyIcon name="visibility" className="text-[15px]" />
          </button>
        ) : null}
      </div>
      {file.summary ? (
        <p className="px-3 pb-1.5 text-[11px] text-on-surface-variant leading-snug">{file.summary}</p>
      ) : null}
      {open ? <DiffHunk lines={lines} /> : null}
    </div>
  );
}

/** Cursor-like single-file card: filename header + +/- badge + always-open hunk. */
export function InlineFileDiffCard({
  file,
  title,
  onOpenFile,
  className = '',
}: {
  file: DiffFileEntry;
  title?: string;
  onOpenFile?: (path: string) => void;
  className?: string;
}) {
  const lines = fileDiffLines(file);
  const { added, removed } = countDelta(lines);
  const label = title || basename(file.path);
  const isHtml = /\.html?$/i.test(file.path);

  return (
    <div
      className={`${CHAT_AGENT_CARD} mt-1.5 ${className}`}
      data-testid="diff-summary-card"
      data-inline="true"
      data-file-count={1}
      data-html-preview={isHtml ? 'true' : undefined}
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b border-outline-variant/20 bg-surface-container-low/60">
        <LegacyIcon name="description" className="text-[15px] text-on-surface-variant shrink-0" />
        <button
          type="button"
          className="text-[12px] font-semibold text-on-surface truncate min-w-0 flex-1 text-left hover:underline"
          title={file.path}
          onClick={() => onOpenFile?.(file.path)}
        >
          {label}
        </button>
        <span className="flex items-center gap-1.5 shrink-0 font-mono text-[11px] font-bold tabular-nums">
          {added > 0 ? <span className="text-emerald-600">+{added}</span> : null}
          {removed > 0 ? <span className="text-rose-600">-{removed}</span> : null}
          {added === 0 && removed === 0 ? (
            <span className="text-on-surface-variant/60">{file.status}</span>
          ) : null}
        </span>
      </div>
      {isHtml ? (
        <div className="px-3 py-2.5 flex items-center justify-between gap-2">
          <p className="text-[11px] text-on-surface-variant min-w-0">
            Preview opens in your system browser
          </p>
          <button
            type="button"
            data-testid="open-html-in-browser"
            onClick={() => onOpenFile?.(file.path)}
            className="shrink-0 rounded-md border border-outline-variant/40 bg-white px-2 py-1 text-[11px] font-semibold text-primary hover:bg-primary/10 transition-colors duration-200"
          >
            Open in browser
          </button>
        </div>
      ) : (
        <DiffHunk lines={lines} />
      )}
    </div>
  );
}

export function DiffSummaryCardView({
  summary,
  t,
  onOpenFile,
}: {
  summary: DiffSummaryData;
  t: (key: string) => string;
  onOpenFile?: (path: string) => void;
}) {
  const count = summary.files.length;
  const inlineSingle = Boolean(summary.inline) && count === 1;

  if (inlineSingle) {
    return (
      <InlineFileDiffCard
        file={summary.files[0]}
        title={summary.title}
        onOpenFile={onOpenFile}
      />
    );
  }

  return (
    <div className={CHAT_AGENT_CARD} data-testid="diff-summary-card" data-file-count={count}>
      <ChatAgentCardHeader
        icon="difference"
        title={summary.title}
        status={
          <ChatAgentCardStatus tone="muted">
            {count === 1 ? t('1 file') : t('{n} files').replace('{n}', String(count))}
          </ChatAgentCardStatus>
        }
      />
      {summary.summary ? (
        <p className="px-3 pt-2.5 text-[12px] text-on-surface leading-relaxed">{summary.summary}</p>
      ) : null}
      <div className="py-1">
        {summary.files.map((file, idx) => (
          <DiffFileRow
            key={file.path}
            file={file}
            t={t}
            onOpen={onOpenFile}
            defaultOpen={idx === 0 || count <= 2}
          />
        ))}
      </div>
    </div>
  );
}
