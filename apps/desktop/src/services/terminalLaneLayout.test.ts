import { describe, expect, it } from 'vitest';

import { expandedLaneSlot } from '../components/terminal-orchestra/terminalLaneLayout';

describe('terminalLaneLayout', () => {
  it('places single lane full bleed', () => {
    expect(expandedLaneSlot(0, 'single')).toMatchObject({ inset: 0 });
  });

  it('places pair lanes side by side', () => {
    const left = expandedLaneSlot(0, 'pair');
    const right = expandedLaneSlot(1, 'pair');
    expect(left.left).toBe(0);
    expect(right.left).toContain('50%');
  });

  it('places split-3 bottom lane full width', () => {
    const bottom = expandedLaneSlot(2, 'split-3');
    expect(bottom.left).toBe(0);
    expect(bottom.right).toBe(0);
    expect(bottom.bottom).toBe(0);
  });
});
