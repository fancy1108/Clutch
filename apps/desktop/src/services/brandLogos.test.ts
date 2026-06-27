import { describe, expect, it } from 'vitest';

import { resolveBrandLogoSrc, resolveToolBrandLogo } from './brandLogos';

describe('brandLogos', () => {
  it('resolves only tools with explicit brand assets', () => {
    expect(resolveToolBrandLogo('claude-cli')).toBeTruthy();
    expect(resolveToolBrandLogo('codex-cli')).toBeUndefined();
    expect(resolveToolBrandLogo('gemini-cli')).toBeUndefined();
  });

  it('does not map clutch agents to a fallback logo', () => {
    expect(resolveBrandLogoSrc({ agentType: 'clutch' })).toBeUndefined();
    expect(resolveBrandLogoSrc({ agent: { agentType: 'clutch' } })).toBeUndefined();
  });

  it('resolves cli agent types with assets', () => {
    expect(resolveBrandLogoSrc({ agentType: 'claude-cli' })).toBeTruthy();
    expect(resolveBrandLogoSrc({ agentType: 'ollama-cli' })).toBeTruthy();
  });
});
