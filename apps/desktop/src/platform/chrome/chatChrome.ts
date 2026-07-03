import type { HostOs } from '../hostOs';
import { isWindowsHost } from '../hostOs';

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

const MAC_CHAT_CHROME: ChatChromeTokens = {
  sidebarContentInset: 30,
  rightContentInset: 30,
  chatEdgePaddingClass: 'px-6',
  chatMaxWidthClass: 'max-w-2xl',
  messageListSpacingClass: 'space-y-8',
  messageRowClass: 'flex gap-4 max-w-[85%] group hover:bg-surface-container-low/35 p-2 rounded-xl transition-colors',
  messageAvatarClass: 'w-9 h-9',
  messageBubblePaddingClass: 'p-4',
  thinkingRowClass: 'flex gap-4 max-w-[85%] p-2 rounded-xl',
  thinkingBubblePaddingClass: 'p-4',
};

const WINDOWS_CHAT_CHROME: ChatChromeTokens = {
  sidebarContentInset: 20,
  rightContentInset: 4,
  chatEdgePaddingClass: 'px-4',
  chatMaxWidthClass: 'max-w-3xl',
  messageListSpacingClass: 'space-y-5',
  messageRowClass: 'flex gap-3 max-w-[85%] group hover:bg-surface-container-low/35 px-1.5 py-1 rounded-xl transition-colors',
  messageAvatarClass: 'w-10 h-10',
  messageBubblePaddingClass: 'px-3 py-1.5',
  thinkingRowClass: 'flex gap-3 max-w-[85%] px-1.5 py-1 rounded-xl',
  thinkingBubblePaddingClass: 'px-3 py-1.5',
};

export function chatChromeForHost(
  hostOs: HostOs,
  sidebarOpen: boolean,
  rightPanelOpen: boolean,
): ChatChromeTokens {
  const base = isWindowsHost(hostOs) ? WINDOWS_CHAT_CHROME : MAC_CHAT_CHROME;
  if (isWindowsHost(hostOs)) {
    return {
      ...base,
      sidebarContentInset: sidebarOpen ? 20 : 8,
      rightContentInset: rightPanelOpen ? 4 : 8,
      chatEdgePaddingClass: sidebarOpen ? 'px-4' : 'px-2',
      chatMaxWidthClass: sidebarOpen ? 'max-w-3xl' : 'max-w-4xl',
    };
  }
  return {
    ...base,
    rightContentInset: rightPanelOpen ? 30 : 30,
  };
}

export function rightPanelSummaryTextClass(hostOs: HostOs): string {
  return isWindowsHost(hostOs)
    ? 'p-3 border border-outline-variant/30 rounded-xl bg-surface-container-low/40 font-mono text-[11px] leading-relaxed space-y-1'
    : 'p-3 border border-outline-variant/30 rounded-xl bg-surface-container-low/40 font-mono text-[10px] space-y-1';
}

export function rightPanelUsesGridTabs(hostOs: HostOs): boolean {
  return isWindowsHost(hostOs);
}
