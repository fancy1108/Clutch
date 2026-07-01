import { describe, expect, it } from 'vitest';

import { resolveBrandLogoSrc, resolveToolBrandLogo } from './brandLogos';

describe('brandLogos', () => {
  it('resolves only tools with explicit brand assets', () => {
    expect(resolveToolBrandLogo('claude-cli')).toBeTruthy();
    expect(resolveToolBrandLogo('codex-cli')).toBeTruthy();
    expect(resolveToolBrandLogo('opencode-cli')).toBeTruthy();
    expect(resolveToolBrandLogo('gemini-cli')).toBeUndefined();
  });

  it('maps clutch agents to the Clutch brand mark', () => {
    expect(resolveBrandLogoSrc({ agentType: 'clutch' })).toBeTruthy();
    expect(resolveBrandLogoSrc({ agent: { agentType: 'clutch' } })).toBeTruthy();
  });

  it('resolves cli agent types with assets', () => {
    expect(resolveBrandLogoSrc({ agentType: 'claude-cli' })).toBeTruthy();
    expect(resolveBrandLogoSrc({ agentType: 'ollama-cli' })).toBeTruthy();
  });
});
