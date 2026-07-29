import { describe, expect, it } from 'vitest';
import {
  createPendingMessage,
  dequeueOnIdle,
  enqueuePendingMessage,
  queuePositionLabel,
  removePendingMessage,
  shouldEnqueueAgentMessage,
} from './chatPendingQueue';

describe('chatPendingQueue (D20)', () => {
  it('enqueues only while plain Clutch Agent is running', () => {
    expect(shouldEnqueueAgentMessage(true, true)).toBe(true);
    expect(shouldEnqueueAgentMessage(true, false)).toBe(false);
    expect(shouldEnqueueAgentMessage(false, true)).toBe(false);
  });

  it('appends trimmed messages with stable ids', () => {
    const first = enqueuePendingMessage('one', [], 1, () => 0.123);
    expect(first).toHaveLength(1);
    expect(first[0]?.text).toBe('one');
    expect(first[0]?.id).toMatch(/^pending_1_/);

    const second = enqueuePendingMessage('  two  ', first, 2, () => 0.456);
    expect(second).toHaveLength(2);
    expect(second[1]?.text).toBe('two');
    expect(enqueuePendingMessage('   ', second)).toEqual(second);
  });

  it('removes a queued item by id', () => {
    const a = createPendingMessage('a', 1, () => 0.1);
    const b = createPendingMessage('b', 2, () => 0.2);
    expect(removePendingMessage(a.id, [a, b])).toEqual([b]);
  });

  it('drains the head when status becomes idle', () => {
    const a = createPendingMessage('a', 1, () => 0.1);
    const b = createPendingMessage('b', 2, () => 0.2);
    expect(dequeueOnIdle('running', 'idle', [a, b])).toEqual({ next: a, rest: [b] });
    expect(dequeueOnIdle('idle', 'idle', [a])).toEqual({ next: null, rest: [a] });
    expect(dequeueOnIdle('running', 'running', [a])).toEqual({ next: null, rest: [a] });
  });

  it('labels queue position for UI', () => {
    expect(queuePositionLabel(0, 'en')).toBe('Queue #1');
    expect(queuePositionLabel(1, 'zh')).toBe('队列 #2');
  });
});
