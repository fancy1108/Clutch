/** D20 — plain Clutch Agent busy message queue helpers. */

export interface PendingChatMessage {
  id: string;
  text: string;
}

export function shouldEnqueueAgentMessage(
  isRunning: boolean,
  isPlainLlmChat: boolean,
): boolean {
  return isRunning && isPlainLlmChat;
}

export function createPendingMessage(
  text: string,
  now = Date.now(),
  random = Math.random,
): PendingChatMessage {
  const trimmed = text.trim();
  const id = `pending_${now}_${random().toString(36).slice(2, 7)}`;
  return { id, text: trimmed };
}

export function enqueuePendingMessage(
  text: string,
  pending: PendingChatMessage[],
  now = Date.now(),
  random = Math.random,
): PendingChatMessage[] {
  const item = createPendingMessage(text, now, random);
  if (!item.text) return pending;
  return [...pending, item];
}

export function removePendingMessage(
  id: string,
  pending: PendingChatMessage[],
): PendingChatMessage[] {
  return pending.filter((item) => item.id !== id);
}

export function dequeueOnIdle(
  prevStatus: string,
  clutchStatus: string,
  pending: PendingChatMessage[],
): { next: PendingChatMessage | null; rest: PendingChatMessage[] } {
  const becameIdle = prevStatus !== 'idle' && clutchStatus === 'idle';
  if (!becameIdle || pending.length === 0) {
    return { next: null, rest: pending };
  }
  const [next, ...rest] = pending;
  return { next: next ?? null, rest };
}

export function queuePositionLabel(index: number, language: 'en' | 'zh'): string {
  const position = index + 1;
  return language === 'zh' ? `队列 #${position}` : `Queue #${position}`;
}
