/** Return true when Enter should submit the chat input (Shift+Enter = newline). */
export function shouldSubmitChatOnEnter(
  e: Pick<KeyboardEvent, 'key' | 'shiftKey' | 'altKey' | 'ctrlKey' | 'metaKey'>,
  isComposing: boolean,
): boolean {
  if (e.key !== 'Enter') return false;
  if (e.shiftKey || e.altKey || e.ctrlKey || e.metaKey) return false;
  return !isComposing;
}
