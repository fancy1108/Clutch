import { describe, expect, it } from 'vitest';

/** Mirrors AgentLiveActivity visibility gate for D19. */
export function shouldShowLiveReasoning(
  reasoningContent: string | null | undefined,
  stepCount: number,
): boolean {
  const hasReasoning = Boolean(reasoningContent?.trim());
  return hasReasoning || stepCount > 0;
}

describe('agent live reasoning (D19)', () => {
  it('shows activity when reasoning exists without tool steps', () => {
    expect(shouldShowLiveReasoning('plan the patch', 0)).toBe(true);
    expect(shouldShowLiveReasoning('  ', 0)).toBe(false);
    expect(shouldShowLiveReasoning(null, 2)).toBe(true);
  });
});
