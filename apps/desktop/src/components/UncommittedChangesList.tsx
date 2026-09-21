/**
 * D57 — Changes tab file list with grouping + collapse + filter.
 *
 * Replaces the flat `uncommitted.map(...)` render in RightPanel that
 * produced one DOM node per file (593 nodes for a 593-file change set),
 * making the panel slow and unnavigable.
 *
 * Mirrors how Cursor / VS Code Source Control handle large change sets:
 *  - Group files by top-level directory
 *  - Each group is collapsible (collapsed by default when total > 50)
 *  - A filter input narrows the list when there are many files
 */
import React, { useMemo, useState } from 'react';import { LegacyIcon } from './ui/LegacyIcon';
import type { UncommittedFile } from '../types';

/** Show the filter box when total files exceed this. */
const FILTER_THRESHOLD = 20;
/** Collapse all groups by default when total files exceed this. */
const COLLAPSE_ALL_THRESHOLD = 50;

function topDir(path: string): string {
  const cleaned = path.replace(/\\/g, '/');
  const parts = cleaned.split('/').filter(Boolean);
  if (parts.length <= 1) return '.';
  return parts[0];
}

function shortName(path: string): string {
  const cleaned = path.replace(/\\/g, '/');
  const parts = cleaned.split('/').filter(Boolean);
  return parts[parts.length - 1] || path;
}

function statusColor(status: string): string {
  if (status === 'A') return 'text-green-500';
  if (status === 'D') return 'text-red-500';
  return 'text-amber-500';
}

interface Group {
  dir: string;
  files: UncommittedFile[];
}

function groupByDir(files: UncommittedFile[]): Group[] {
  const map = new Map<string, UncommittedFile[]>();
  for (const f of files) {
    const d = topDir(f.name);
    const arr = map.get(d);
    if (arr) arr.push(f);
    else map.set(d, [f]);
  }
  // Sort groups alphabetically; "." (root) last.
  const groups = [...map.entries()].map(([dir, fs]) => ({ dir, files: fs }));
  groups.sort((a, b) => {
    if (a.dir === '.' && b.dir !== '.') return 1;
    if (b.dir === '.' && a.dir !== '.') return -1;
    return a.dir.localeCompare(b.dir);
  });
  return groups;
}

export function UncommittedChangesList({
  files,
  selectedFile,
  onSelect,
  onOpenFile,
  t,
  isGitRepo = true,
}: {
  files: UncommittedFile[];
  selectedFile: string | null;
  onSelect: (name: string) => void;
  onOpenFile?: (name: string) => void;
  t: (key: string) => string;
  isGitRepo?: boolean;
}) {
  const [filter, setFilter] = useState('');

  const total = files.length;
  const showFilter = total > FILTER_THRESHOLD;

  // Initialize open groups once: all open when total is small, all closed
  // when total exceeds the collapse threshold.
  const [openGroups, setOpenGroups] = useState<Set<string>>(() => {
    if (total <= COLLAPSE_ALL_THRESHOLD) {
      return new Set(groupByDir(files).map((g) => g.dir));
    }
    return new Set();
  });

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return files;
    return files.filter((f) => f.name.toLowerCase().includes(q));
  }, [files, filter]);

  const groups = useMemo(() => groupByDir(filtered), [filtered]);

  const toggleGroup = (dir: string) => {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(dir)) next.delete(dir);
      else next.add(dir);
      return next;
    });
  };

  if (total === 0) {
    return (
      <div
        className="py-8 text-center bg-surface-container-low/40 rounded-xl border border-dashed border-outline-variant mt-2 text-on-surface-variant/60"
        data-testid="uncommitted-changes-empty"
      >
        <LegacyIcon
          name={isGitRepo ? 'difference' : 'folder_off'}
          className="text-[28px] mb-2"
        />
        <p className="text-[11px] font-medium">
          {isGitRepo ? t('No uncommitted changes') : t('Not a Git repository')}
        </p>
        {!isGitRepo ? (
          <p className="mt-1 px-6 text-[10px] leading-relaxed text-on-surface-variant/50">
            {t('This workspace is not a Git repository; changes cannot be tracked here.')}
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="uncommitted-changes-list">
      {showFilter ? (
        <div className="relative">
          <LegacyIcon
            name="search"
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[14px] text-on-surface-variant/50 pointer-events-none"
          />
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder={t('Filter files...')}
            className="w-full pl-8 pr-2 py-1.5 text-[11px] rounded-lg border border-outline-variant/40 bg-white/70 focus:outline-none focus:border-primary/50 focus:bg-white"
            data-testid="uncommitted-changes-filter"
          />
        </div>
      ) : null}

      {filtered.length === 0 && filter ? (
        <p className="py-4 text-center text-[11px] text-on-surface-variant/60">
          {t('No projects match your filter')}
        </p>
      ) : null}

      {groups.map((group) => {
        const open = openGroups.has(group.dir) || filtered.length <= COLLAPSE_ALL_THRESHOLD;
        const dirLabel = group.dir === '.' ? t('(root)') : group.dir;
        return (
          <div key={group.dir} data-testid={`uncommitted-group-${group.dir}`}>
            <button
              type="button"
              onClick={() => toggleGroup(group.dir)}
              className="flex items-center gap-1.5 w-full px-1.5 py-1 rounded-md hover:bg-surface-container-low/60 transition-colors"
              aria-expanded={open}
            >
              <LegacyIcon
                name={open ? 'expand_more' : 'chevron_right'}
                className="text-[14px] text-on-surface-variant shrink-0"
              />
              <LegacyIcon
                name="folder"
                className="text-[14px] text-on-surface-variant/70 shrink-0"
              />
              <span className="text-[11px] font-semibold text-on-surface truncate flex-1 text-left">
                {dirLabel}
              </span>
              <span className="text-[9px] font-bold text-on-surface-variant/60 tabular-nums shrink-0">
                {group.files.length}
              </span>
            </button>
            {open ? (
              <div className="space-y-0.5 mt-0.5">
                {group.files.map((file) => {
                  const isActive = file.name === selectedFile;
                  return (
                    <div
                      key={file.name}
                      onClick={() => onSelect(file.name)}
                      className={`flex items-center justify-between pl-6 pr-1 py-1.5 rounded-lg transition-colors cursor-pointer group ${
                        isActive
                          ? 'bg-surface-container-low border border-outline-variant/30 font-bold'
                          : 'hover:bg-surface-container-low'
                      }`}
                    >
                      <div className="flex items-center gap-2 overflow-hidden min-w-0">
                        <span
                          className={`text-[10px] font-bold w-4 text-center shrink-0 ${statusColor(file.status)}`}
                        >
                          {file.status}
                        </span>
                        <span
                          className="text-[11px] truncate text-on-surface min-w-0"
                          title={file.name}
                        >
                          {shortName(file.name)}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenFile?.(file.name);
                        }}
                        className="shrink-0 p-1 rounded-md text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface opacity-0 group-hover:opacity-100 transition-opacity"
                        title={t('Preview file')}
                        aria-label={t('Preview file')}
                      >
                        <LegacyIcon name="visibility" className="text-[14px]" />
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
