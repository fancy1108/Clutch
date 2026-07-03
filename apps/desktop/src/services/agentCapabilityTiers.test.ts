import { describe, expect, it } from 'vitest';
import {
  getAgentCapabilityTier,
  settingsTabForAgentType,
} from './agentCapabilityTiers';

describe('agentCapabilityTiers', () => {
  it('classifies clutch as full', () => {
    expect(getAgentCapabilityTier('clutch')).toBe('full');
  });

  it('classifies claude and opencode as readOnlyScan', () => {
    expect(getAgentCapabilityTier('claude-cli')).toBe('readOnlyScan');
    expect(getAgentCapabilityTier('opencode-cli')).toBe('readOnlyScan');
  });

  it('classifies other CLIs as comingSoon', () => {
    expect(getAgentCapabilityTier('codex-cli')).toBe('comingSoon');
    expect(getAgentCapabilityTier('ollama-cli')).toBe('comingSoon');
  });

  it('maps settings tabs for in-scope agents', () => {
    expect(settingsTabForAgentType('clutch')).toBe('clutch');
    expect(settingsTabForAgentType('claude-cli')).toBe('claude-cli');
    expect(settingsTabForAgentType('opencode-cli')).toBe('opencode-cli');
    expect(settingsTabForAgentType('codex-cli')).toBeNull();
  });
});
