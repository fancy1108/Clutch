import type React from 'react';

/** Matches sidebar/right-panel CSS transition in App.tsx */
export const TERMINAL_CHROME_TRANSITION_MS = 300;

/** Gutter when a side panel is collapsed but its toggle pill still protrudes. */
export const TERMINAL_COLLAPSED_TOGGLE_GUTTER_PX = 16;

export function buildTerminalLayoutChromeKey(parts: {
  sidebarWidth: number;
  rightPanelWidth: number;
  dockHeight: number;
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
}): string {
  return [
    parts.sidebarWidth,
    parts.rightPanelWidth,
    parts.dockHeight,
    parts.sidebarOpen ? 1 : 0,
    parts.rightPanelOpen ? 1 : 0,
  ].join(':');
}

/** Schedule xterm refits after chrome transitions complete. */
export function scheduleTerminalLayoutRefit(bump: () => void): () => void {
  bump();
  const t1 = window.setTimeout(bump, TERMINAL_CHROME_TRANSITION_MS + 24);
  const t2 = window.setTimeout(bump, TERMINAL_CHROME_TRANSITION_MS * 2 + 48);
  return () => {
    window.clearTimeout(t1);
    window.clearTimeout(t2);
  };
}

/** Refit a single xterm after flex/grid layout settles (multi-lane resize). */
export function scheduleXtermRefit(refit: () => void): () => void {
  refit();
  let raf2 = 0;
  const raf1 = window.requestAnimationFrame(() => {
    refit();
    raf2 = window.requestAnimationFrame(refit);
  });
  const t1 = window.setTimeout(refit, 48);
  const t2 = window.setTimeout(refit, TERMINAL_CHROME_TRANSITION_MS + 32);
  return () => {
    window.cancelAnimationFrame(raf1);
    if (raf2) window.cancelAnimationFrame(raf2);
    window.clearTimeout(t1);
    window.clearTimeout(t2);
  };
}
export const XTERM_KEEPALIVE_STYLE: React.CSSProperties = {
  position: 'fixed',
  left: -10000,
  top: 0,
  width: 960,
  height: 540,
  opacity: 0,
  overflow: 'hidden',
  pointerEvents: 'none',
  zIndex: -1,
};

/** Grid cell wrapper — `contents` removes the slot when lane is collapsed. */
export function lanePaneOuterClass(collapsed: boolean): string {
  return collapsed ? 'contents' : 'flex flex-col min-h-0 h-full min-w-0 w-full';
}

export function lanePaneHostClass(collapsed: boolean): string {
  return collapsed ? 'flex flex-col h-full' : 'flex flex-col flex-1 min-h-0 h-full w-full';
}

export function lanePaneHostStyle(collapsed: boolean): React.CSSProperties | undefined {
  return collapsed ? XTERM_KEEPALIVE_STYLE : undefined;
}
