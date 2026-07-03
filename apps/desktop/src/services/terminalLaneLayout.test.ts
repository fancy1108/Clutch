import { describe, expect, it, vi } from 'vitest';

import { expandedLaneSlot, wakeXtermTerminal } from '../components/terminal-orchestra/terminalLaneLayout';

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

  it('wakeXtermTerminal fits and refreshes when host has size', () => {
    const host = { clientWidth: 320, clientHeight: 200 } as HTMLElement;
    const refresh = vi.fn();
    const term = { rows: 24, refresh };
    const fitAddon = { fit: vi.fn() };
    expect(wakeXtermTerminal(term, fitAddon, host)).toBe(true);
    expect(fitAddon.fit).toHaveBeenCalled();
    expect(refresh).toHaveBeenCalledWith(0, 23);
  });
});
