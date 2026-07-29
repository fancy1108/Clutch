/**
 * D47 — clickable chips for assistant-turn filesChanged (DECISIONS D42 preview).
 */
import React, { useEffect, useState } from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import { isImageWorkspacePath } from '../services/workspacePathLinks';
import { workspaceMediaUrl } from '../services/sidecarUrl';

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

export function FilesChangedChips({
  paths,
  onOpen,
  label,
}: {
  paths: string[];
  onOpen?: (path: string) => void;
  label: string;
}) {
  const unique = [...new Set(paths.map((p) => p.trim()).filter(Boolean))];
  if (unique.length === 0) return null;

  return (
    <div className="mt-3 flex flex-col gap-1.5" data-testid="files-changed-chips">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant/70">
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {unique.map((path) => {
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
        })}
      </div>
    </div>
  );
}
