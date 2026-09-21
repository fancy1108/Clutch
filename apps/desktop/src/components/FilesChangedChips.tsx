/**
 * D47 — clickable chips for assistant-turn filesChanged (DECISIONS D42 preview).
 *
 * D57 — collapse large file lists to keep the chat feed compact.
 * When files exceed `COLLAPSE_THRESHOLD`, only the first `PREVIEW_COUNT`
 * chips render by default; a "Show all (N)" expander reveals the rest
 * inside a scrollable container. Mirrors how Cursor keeps a multi-hundred-
 * file change list from flooding the chat / LLM context.
 */
import React, { useEffect, useState } from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import { isImageWorkspacePath } from '../services/workspacePathLinks';
import { workspaceMediaUrl } from '../services/sidecarUrl';

/** Render chips inline up to this count; beyond it, collapse. */
const COLLAPSE_THRESHOLD = 8;
/** How many chips to preview when collapsed. */
const PREVIEW_COUNT = 8;
/** Max height (px) of the expanded chip container before it scrolls. */
const EXPANDED_MAX_HEIGHT = 220;

function basename(path: string): string {
  const cleaned = path.replace(/\\/g, '/');
  const parts = cleaned.split('/').filter(Boolean);
  return parts[parts.length - 1] || cleaned;
}

function ImageChipThumb({ path }: { path: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    void workspaceMediaUrl(path).then((url) => {
      if (!cancelled) setSrc(url);
    });
    return () => {
      cancelled = true;
    };
  }, [path]);
  if (!src) {
    return <LegacyIcon name="image" className="text-[15px] text-on-surface-variant flex-shrink-0" />;
  }
  return (
    <img
      src={src}
      alt=""
      className="w-[22px] h-[22px] rounded object-cover flex-shrink-0 border border-outline-variant/30"
    />
  );
}

function Chip({
  path,
  onOpen,
}: {
  path: string;
  onOpen?: (path: string) => void;
}) {
  const name = basename(path);
  const isImage = isImageWorkspacePath(path);
  return (
    <button
      key={path}
      type="button"
      title={path}
      onClick={() => onOpen?.(path)}
      className="inline-flex items-center gap-1.5 pl-1.5 pr-2 py-0.5 max-w-[220px] rounded-lg border border-outline-variant/40 bg-white/70 text-[11px] font-medium text-primary hover:bg-primary/5 hover:border-primary/40 transition-colors"
    >
      {isImage ? (
        <ImageChipThumb path={path} />
      ) : (
        <LegacyIcon name="description" className="text-[15px] text-on-surface-variant flex-shrink-0" />
      )}
      <span className="truncate font-mono">{name}</span>
    </button>
  );
}

export function FilesChangedChips({
  paths,
  onOpen,
  label,
  t,
}: {
  paths: string[];
  onOpen?: (path: string) => void;
  label: string;
  t: (key: string) => string;
}) {
  const unique = [...new Set(paths.map((p) => p.trim()).filter(Boolean))];
  if (unique.length === 0) return null;

  const [expanded, setExpanded] = useState(false);
  const total = unique.length;
  const shouldCollapse = total > COLLAPSE_THRESHOLD;
  const visible = shouldCollapse && !expanded ? unique.slice(0, PREVIEW_COUNT) : unique;
  const hiddenCount = total - PREVIEW_COUNT;

  return (
    <div className="mt-3 flex flex-col gap-1.5" data-testid="files-changed-chips">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant/70">
          {label}
        </span>
        {shouldCollapse ? (
          <span className="text-[10px] font-medium text-on-surface-variant/55 tabular-nums">
            ({total})
          </span>
        ) : null}
      </div>
      {expanded && shouldCollapse ? (
        <div
          className="flex flex-wrap gap-1.5 overflow-y-auto pr-1"
          style={{ maxHeight: EXPANDED_MAX_HEIGHT }}
          data-testid="files-changed-chips-expanded"
        >
          {unique.map((path) => (
            <Chip key={path} path={path} onOpen={onOpen} />
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {visible.map((path) => (
            <Chip key={path} path={path} onOpen={onOpen} />
          ))}
        </div>
      )}
      {shouldCollapse ? (
        <button
          type="button"
          data-testid="files-changed-chips-toggle"
          className="self-start text-[10px] font-semibold text-primary hover:underline"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded
            ? t('Show less')
            : t('Show all ({n})').replace('{n}', String(hiddenCount))}
        </button>
      ) : null}
    </div>
  );
}
