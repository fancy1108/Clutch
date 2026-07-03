import { describe, expect, it } from 'vitest';
import { formatDispatchTime, parseDispatchTimestamp } from './formatTime';

describe('formatDispatchTime', () => {
  it('converts legacy UTC HH:MM to local time', () => {
    const date = parseDispatchTimestamp('02:45');
    expect(date).not.toBeNull();
    expect(formatDispatchTime('02:45')).toBe(
      date!.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false }),
    );
  });

  it('formats ISO UTC timestamps in local time', () => {
    const iso = '2026-07-03T02:45:00.279163+00:00';
    const date = parseDispatchTimestamp(iso);
    expect(formatDispatchTime(iso)).toBe(
      date!.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false }),
    );
  });

  it('returns original string when unparseable', () => {
    expect(formatDispatchTime('not-a-time')).toBe('not-a-time');
  });
});
