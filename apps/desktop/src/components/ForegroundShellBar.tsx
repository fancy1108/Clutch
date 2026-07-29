/**
 * D34 — foreground shell bar with one-click move to background.
 */
import React from 'react';
import { LegacyIcon } from './ui/LegacyIcon';

export interface ForegroundShellState {
  command: string;
  title: string;
  cwd?: string;
}

export function ForegroundShellBar({
  shell,
  t,
  onMoveToBackground,
}: {
  shell: ForegroundShellState;
  t: (key: string) => string;
  onMoveToBackground: () => void;
}) {
  return (
    <div
      data-testid="foreground-shell-bar"
      className="w-full max-w-3xl mx-auto px-3 pb-2"
    >
      <div
        className="flex items-center gap-2 rounded-lg border border-amber-500/40 bg-amber-500/5 px-3 py-2"
        data-testid="foreground-shell-chip"
      >
        <LegacyIcon
          name="terminal"
          className="text-[15px] text-amber-700 shrink-0"
        />
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-semibold text-on-surface truncate">
            {shell.title || shell.command}
          </div>
          <div className="text-[10px] text-on-surface-variant/70">
            {t('Foreground command running')}
          </div>
        </div>
        <button
          type="button"
          data-testid="move-fg-to-background"
          className="shrink-0 rounded-md bg-primary px-2.5 py-1 text-[10px] font-semibold text-on-primary hover:bg-primary/90"
          onClick={onMoveToBackground}
        >
          {t('Move to background')}
        </button>
      </div>
    </div>
  );
}
