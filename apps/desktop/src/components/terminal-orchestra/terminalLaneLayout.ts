import type React from 'react';
import type { CSSProperties } from 'react';
import type { LaneGridLayout } from '../../services/terminalOrchestraUtils';

/** Matches sidebar/right-panel CSS transition in App.tsx */
export const TERMINAL_CHROME_TRANSITION_MS = 300;

/** Gutter when a side panel is collapsed but its toggle pill still protrudes. */
export const TERMINAL_COLLAPSED_TOGGLE_GUTTER_PX = 16;

/** Gap between visible lane slots (Tailwind gap-3). */
export const TERMINAL_LANE_SLOT_GAP = '0.75rem';

/** Off-screen dimensions for collapsed lanes — xterm stays mounted and refits here. */
export const LANE_KEEPALIVE_WIDTH_PX = 960;
export const LANE_KEEPALIVE_HEIGHT_PX = 540;

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
  const t3 = window.setTimeout(refit, TERMINAL_CHROME_TRANSITION_MS * 2 + 64);
  return () => {
    window.cancelAnimationFrame(raf1);
    if (raf2) window.cancelAnimationFrame(raf2);
    window.clearTimeout(t1);
    window.clearTimeout(t2);
    window.clearTimeout(t3);
  };
}

/** @deprecated Prefer LANE_KEEPALIVE_SLOT — kept for TerminalOrchestraWorkspace hide. */
export const XTERM_KEEPALIVE_STYLE: React.CSSProperties = {
  position: 'fixed',
  left: -10000,
  top: 0,
  width: LANE_KEEPALIVE_WIDTH_PX,
  height: LANE_KEEPALIVE_HEIGHT_PX,
  opacity: 0,
  overflow: 'hidden',
  pointerEvents: 'none',
  zIndex: -1,
};

/** Collapsed / queued lane slot — same parent as expanded lanes to avoid PTY remount. */
export const LANE_KEEPALIVE_SLOT: CSSProperties = {
  position: 'absolute',
  left: -10000,
  top: 0,
  width: LANE_KEEPALIVE_WIDTH_PX,
  height: LANE_KEEPALIVE_HEIGHT_PX,
  opacity: 0,
  overflow: 'hidden',
  pointerEvents: 'none',
  zIndex: -1,
};

const SLOT_BASE: CSSProperties = {
  position: 'absolute',
  minWidth: 0,
  minHeight: 0,
};

/** Absolute slot for an expanded lane within the stage (responsive, gap-aware). */
export function expandedLaneSlot(
  slotIndex: number,
  layout: LaneGridLayout,
): CSSProperties {
  const gap = TERMINAL_LANE_SLOT_GAP;
  const halfWidth = `calc((100% - ${gap}) / 2)`;
  const halfHeight = `calc((100% - ${gap}) / 2)`;

  if (layout === 'single') {
    return { ...SLOT_BASE, inset: 0 };
  }

  if (layout === 'pair') {
    return {
      ...SLOT_BASE,
      top: 0,
      bottom: 0,
      width: halfWidth,
      left: slotIndex === 0 ? 0 : `calc(50% + ${gap} / 2)`,
    };
  }

  if (layout === 'split-3') {
    const topHeight = `calc((100% - ${gap}) * 0.425)`;
    const bottomHeight = `calc((100% - ${gap}) * 0.575)`;
    if (slotIndex < 2) {
      return {
        ...SLOT_BASE,
        top: 0,
        height: topHeight,
        width: halfWidth,
        left: slotIndex === 0 ? 0 : `calc(50% + ${gap} / 2)`,
      };
    }
    return {
      ...SLOT_BASE,
      left: 0,
      right: 0,
      bottom: 0,
      height: bottomHeight,
    };
  }

  const col = slotIndex % 2;
  const row = Math.floor(slotIndex / 2);
  return {
    ...SLOT_BASE,
    width: halfWidth,
    height: halfHeight,
    left: col === 0 ? 0 : `calc(50% + ${gap} / 2)`,
    top: row === 0 ? 0 : `calc(50% + ${gap} / 2)`,
  };
}

/** Grid cell wrapper — `contents` removes the slot when lane is collapsed. */
export function lanePaneOuterClass(collapsed: boolean): string {
  return collapsed ? 'contents' : 'flex flex-col min-h-0 h-full min-w-0 w-full';
}

export function lanePaneHostClass(collapsed: boolean): string {
  return collapsed ? 'flex flex-col h-full' : 'flex flex-col flex-1 min-h-0 h-full w-full';
}

export function lanePaneHostStyle(collapsed: boolean): React.CSSProperties | undefined {
  return collapsed ? LANE_KEEPALIVE_SLOT : undefined;
}
