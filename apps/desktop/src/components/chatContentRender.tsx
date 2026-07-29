import React, { useState } from 'react';
import {
  AT_PATH_RE,
  CODE_BLOCK_COLLAPSE_LINES,
  FILE_MARKER_RE,
  findPathCandidates,
  stripPathPunctuation,
} from '../services/workspacePathLinks';
import { LegacyIcon } from './ui/LegacyIcon';

export type ChatRenderHandlers = {
  onOpenPath?: (path: string) => void;
  onPreviewSnippet?: (name: string, content: string) => void;
};

function PathLink({
  path,
  onOpenPath,
  children,
}: {
  path: string;
  onOpenPath?: (path: string) => void;
  children?: React.ReactNode;
}) {
  const cleaned = stripPathPunctuation(path);
  return (
    <button
      type="button"
      className="inline text-primary font-medium hover:underline font-mono text-[12px] align-baseline"
      title={cleaned}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onOpenPath?.(cleaned);
      }}
    >
      {children ?? cleaned}
    </button>
  );
}

function linkifyPlainLine(line: string, keyPrefix: string, handlers: ChatRenderHandlers): React.ReactNode {
  // [file: path] markers first
  const markerParts: React.ReactNode[] = [];
  let cursor = 0;
  const markerRe = new RegExp(FILE_MARKER_RE.source, 'gi');
  let m: RegExpExecArray | null;
  const hits: Array<{ start: number; end: number; path: string; kind: 'file' | 'at' | 'path' }> = [];

  while ((m = markerRe.exec(line)) !== null) {
    hits.push({ start: m.index, end: m.index + m[0].length, path: m[1].trim(), kind: 'file' });
  }
  const atRe = new RegExp(AT_PATH_RE.source, 'g');
  while ((m = atRe.exec(line)) !== null) {
    hits.push({ start: m.index, end: m.index + m[0].length, path: m[1], kind: 'at' });
  }
  for (const c of findPathCandidates(line)) {
    const overlaps = hits.some((h) => !(c.end <= h.start || c.start >= h.end));
    if (!overlaps) hits.push({ start: c.start, end: c.end, path: c.raw, kind: 'path' });
  }
  hits.sort((a, b) => a.start - b.start);

  if (hits.length === 0) {
    return line;
  }

  hits.forEach((hit, idx) => {
    if (hit.start > cursor) {
      markerParts.push(line.slice(cursor, hit.start));
    }
    const label =
      hit.kind === 'file' ? `[file: ${stripPathPunctuation(hit.path)}]` : hit.kind === 'at' ? `@${stripPathPunctuation(hit.path)}` : hit.path;
    markerParts.push(
      <PathLink key={`${keyPrefix}-${idx}`} path={hit.path} onOpenPath={handlers.onOpenPath}>
        {label}
      </PathLink>,
    );
    cursor = hit.end;
  });
  if (cursor < line.length) markerParts.push(line.slice(cursor));
  return <>{markerParts}</>;
}

function formatInline(str: string, handlers: ChatRenderHandlers, keyPrefix: string): React.ReactNode {
  // Split by inline code / bold roughly, then linkify remaining text segments
  const parts: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = re.exec(str)) !== null) {
    if (match.index > last) {
      parts.push(
        <React.Fragment key={`${keyPrefix}-t-${i}`}>
          {linkifyPlainLine(str.slice(last, match.index), `${keyPrefix}-l-${i}`, handlers)}
        </React.Fragment>,
      );
    }
    const token = match[0];
    if (token.startsWith('**')) {
      parts.push(
        <strong key={`${keyPrefix}-b-${i}`} className="font-bold text-on-surface">
          {token.slice(2, -2)}
        </strong>,
      );
    } else {
      parts.push(
        <code
          key={`${keyPrefix}-c-${i}`}
          className="bg-neutral-200/60 dark:bg-neutral-800 text-on-surface px-1 py-0.5 rounded font-mono text-[11px] border border-outline-variant/20 mx-0.5"
        >
          {token.slice(1, -1)}
        </code>,
      );
    }
    last = match.index + token.length;
    i += 1;
  }
  if (last < str.length) {
    parts.push(
      <React.Fragment key={`${keyPrefix}-t-end`}>
        {linkifyPlainLine(str.slice(last), `${keyPrefix}-l-end`, handlers)}
      </React.Fragment>,
    );
  }
  return parts.length ? <>{parts}</> : linkifyPlainLine(str, keyPrefix, handlers);
}

function CodeBlock({
  lang,
  code,
  handlers,
}: {
  lang: string;
  code: string;
  handlers: ChatRenderHandlers;
}) {
  const [expanded, setExpanded] = useState(false);
  const lines = code.split('\n');
  const collapsed = !expanded && lines.length > CODE_BLOCK_COLLAPSE_LINES;
  const shown = collapsed ? lines.slice(0, CODE_BLOCK_COLLAPSE_LINES).join('\n') : code;
  const name = lang ? `snippet.${lang}` : 'snippet.txt';

  return (
    <div className="my-2 rounded-xl border border-outline-variant/40 overflow-hidden bg-neutral-900 text-neutral-200">
      <div className="flex items-center justify-between px-3 py-1.5 bg-neutral-800/80 border-b border-neutral-700/60">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
          {lang || 'code'}
        </span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="text-[10px] font-semibold px-2 py-0.5 rounded-md hover:bg-neutral-700 text-neutral-300"
            onClick={() => void navigator.clipboard.writeText(code)}
          >
            Copy
          </button>
          <button
            type="button"
            className="text-[10px] font-semibold px-2 py-0.5 rounded-md hover:bg-neutral-700 text-neutral-300"
            onClick={() => handlers.onPreviewSnippet?.(name, code)}
          >
            Preview
          </button>
        </div>
      </div>
      <pre className="px-3 py-2 text-[11px] font-mono overflow-x-auto overflow-y-auto max-h-64 leading-relaxed whitespace-pre">
        {shown}
        {collapsed ? '\n…' : ''}
      </pre>
      {lines.length > CODE_BLOCK_COLLAPSE_LINES ? (
        <button
          type="button"
          className="w-full text-[10px] font-semibold py-1.5 border-t border-neutral-700/60 text-neutral-400 hover:bg-neutral-800"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? 'Collapse' : `Expand (${lines.length} lines)`}
        </button>
      ) : null}
    </div>
  );
}

/** Markdown-ish chat renderer with fences, path links, and [file:]/@ chips. */
export function renderChatMarkdown(text: string, handlers: ChatRenderHandlers = {}): React.ReactNode {
  if (!text) return null;

  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let inFence = false;
  let fenceLang = '';
  let fenceLines: string[] = [];
  let inBlockquote = false;
  let blockquoteLines: string[] = [];
  let isAlert = false;
  let alertType = '';

  const flushBlockquote = (key: number) => {
    if (blockquoteLines.length === 0 && !isAlert) return;
    const content = blockquoteLines.join('\n');
    blockquoteLines = [];
    inBlockquote = false;
    if (isAlert) {
      elements.push(
        <div
          key={`alert-${key}`}
          className="p-3.5 my-3 rounded-xl border border-blue-200/80 bg-blue-50/50 flex items-start gap-2.5"
        >
          <LegacyIcon name="info" className="text-[18px] mt-0.5 text-blue-900" />
          <div className="flex-1 space-y-1">
            <div className="text-[11px] font-bold tracking-wide uppercase text-blue-900">{alertType}</div>
            <div className="text-[12.5px] leading-relaxed text-on-surface">
              {formatInline(content, handlers, `alert-${key}`)}
            </div>
          </div>
        </div>,
      );
    } else {
      elements.push(
        <blockquote
          key={`bq-${key}`}
          className="p-3 my-2 border border-neutral-200/80 rounded-xl text-neutral-500 italic text-[12.5px]"
        >
          {formatInline(content, handlers, `bq-${key}`)}
        </blockquote>,
      );
    }
    isAlert = false;
    alertType = '';
  };

  const flushFence = (key: number) => {
    if (!inFence) return;
    elements.push(
      <CodeBlock key={`fence-${key}`} lang={fenceLang} code={fenceLines.join('\n')} handlers={handlers} />,
    );
    inFence = false;
    fenceLang = '';
    fenceLines = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith('```')) {
      if (inFence) {
        flushFence(i);
      } else {
        if (inBlockquote) flushBlockquote(i);
        inFence = true;
        fenceLang = trimmed.slice(3).trim();
        fenceLines = [];
      }
      continue;
    }

    if (inFence) {
      fenceLines.push(line);
      continue;
    }

    if (trimmed.startsWith('>')) {
      let content = line.substring(line.indexOf('>') + 1);
      if (content.startsWith(' ')) content = content.substring(1);
      const alertMatch = content.match(/^\[!(IMPORTANT|WARNING|NOTE|TIP)\]/i);
      if (alertMatch) {
        isAlert = true;
        alertType = alertMatch[1].toUpperCase();
        inBlockquote = true;
      } else {
        blockquoteLines.push(content);
        inBlockquote = true;
      }
      continue;
    }

    if (inBlockquote) flushBlockquote(i);

    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={i} className="text-base font-extrabold text-neutral-900 border-b border-neutral-200 pb-1.5 mb-3 mt-3">
          {trimmed.substring(2)}
        </h1>,
      );
      continue;
    }
    if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="text-sm font-bold text-neutral-800 mt-4 mb-1.5">
          {trimmed.substring(3)}
        </h2>,
      );
      continue;
    }
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="text-xs font-bold text-neutral-800 mt-3 mb-1">
          {trimmed.substring(4)}
        </h3>,
      );
      continue;
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <div key={i} className="flex items-start gap-2 pl-2 my-1 text-on-surface text-[13px]">
          <span className="w-1 h-1 mt-2 rounded bg-neutral-400 flex-shrink-0" />
          <span>{formatInline(trimmed.substring(2), handlers, `li-${i}`)}</span>
        </div>,
      );
      continue;
    }

    if (trimmed === '') {
      elements.push(<div key={i} className="h-2" />);
    } else {
      elements.push(
        <p key={i} className="my-1.5 text-on-surface text-[13px] leading-relaxed">
          {formatInline(line, handlers, `p-${i}`)}
        </p>,
      );
    }
  }

  if (inFence) flushFence(lines.length);
  if (inBlockquote) flushBlockquote(lines.length);

  return <div className="space-y-1 select-text">{elements}</div>;
}
