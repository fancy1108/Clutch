import { describe, expect, it } from 'vitest';
import { formatStepMeter, formatTokenMeter, inputOutputPercents } from './sessionUsage';

describe('sessionUsage', () => {
  it('marks estimated token counts with a tilde', () => {
    expect(formatTokenMeter(1200, true)).toBe('~1,200');
    expect(formatTokenMeter(1200, false)).toBe('1,200');
    expect(formatTokenMeter(0, true)).toBe('—');
  });

  it('formats step meters as used/max', () => {
    expect(formatStepMeter(4, 24)).toBe('4/24');
    expect(formatStepMeter(0, 24)).toBe('0/24');
  });

  it('splits input/output percents', () => {
    expect(inputOutputPercents(75, 25)).toEqual({ inPct: 75, outPct: 25 });
    expect(inputOutputPercents(0, 0)).toEqual({ inPct: 50, outPct: 50 });
  });
});
