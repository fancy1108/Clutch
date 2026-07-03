import type { HostOs } from '../hostOs';

export type ChatChromeTokens = {
  sidebarContentInset: number;
  rightContentInset: number;
  chatEdgePaddingClass: string;
  chatMaxWidthClass: string;
  messageListSpacingClass: string;
  messageRowClass: string;
  messageAvatarClass: string;
  messageBubblePaddingClass: string;
  thinkingRowClass: string;
  thinkingBubblePaddingClass: string;
};

/** Gutter between main workspace and right supervision panel (both platforms). */
const RIGHT_PANEL_CONTENT_INSET_PX = 30;

/** Shared compact workspace chrome (macOS + Windows). Sidebars remain platform-specific. */
const COMPACT_CHAT_CHROME: ChatChromeTokens = {
  sidebarContentInset: 20,
  rightContentInset: RIGHT_PANEL_CONTENT_INSET_PX,
  chatEdgePaddingClass: 'px-4',
  chatMaxWidthClass: 'max-w-3xl',
  messageListSpacingClass: 'space-y-5',
  messageRowClass:
    'flex gap-3 max-w-[85%] group hover:bg-surface-container-low/35 px-1.5 py-1 rounded-xl transition-colors',
  messageAvatarClass: 'w-10 h-10',
  messageBubblePaddingClass: 'px-3 py-1.5',
  thinkingRowClass: 'flex gap-3 max-w-[85%] px-1.5 py-1 rounded-xl',
  thinkingBubblePaddingClass: 'px-3 py-1.5',
};

export function chatChromeForHost(
  _hostOs: HostOs,
  sidebarOpen: boolean,
  _rightPanelOpen: boolean,
): ChatChromeTokens {
  return {
    ...COMPACT_CHAT_CHROME,
    sidebarContentInset: sidebarOpen ? 20 : 8,
    rightContentInset: RIGHT_PANEL_CONTENT_INSET_PX,
    chatEdgePaddingClass: sidebarOpen ? 'px-4' : 'px-2',
    chatMaxWidthClass: sidebarOpen ? 'max-w-3xl' : 'max-w-4xl',
  };
}

export function rightPanelSummaryTextClass(_hostOs: HostOs): string {
  return 'p-3 border border-outline-variant/30 rounded-xl bg-surface-container-low/40 font-mono text-[11px] leading-relaxed space-y-1';
}

export function rightPanelUsesGridTabs(_hostOs: HostOs): boolean {
  return true;
}
