import { describe, expect, it } from 'vitest';
import {
  getAgentCapabilityTier,
  settingsTabForAgentType,
} from './agentCapabilityTiers';

describe('agentCapabilityTiers', () => {
  it('classifies clutch as full', () => {
    expect(getAgentCapabilityTier('clutch')).toBe('full');
  });

  it('classifies claude, opencode, and mimo as readOnlyScan', () => {
    expect(getAgentCapabilityTier('claude-cli')).toBe('readOnlyScan');
    expect(getAgentCapabilityTier('opencode-cli')).toBe('readOnlyScan');
    expect(getAgentCapabilityTier('mimo-cli')).toBe('readOnlyScan');
  });

  it('classifies More CLIs as readOnlyScan', () => {
    expect(getAgentCapabilityTier('codex-cli')).toBe('readOnlyScan');
    expect(getAgentCapabilityTier('ollama-cli')).toBe('readOnlyScan');
    expect(getAgentCapabilityTier('aider-cli')).toBe('readOnlyScan');
  });

  it('maps settings tabs for in-scope agents', () => {
    expect(settingsTabForAgentType('clutch')).toBe('clutch');
    expect(settingsTabForAgentType('claude-cli')).toBe('claude-cli');
    expect(settingsTabForAgentType('opencode-cli')).toBe('opencode-cli');
    expect(settingsTabForAgentType('mimo-cli')).toBe('mimo-cli');
    expect(settingsTabForAgentType('codex-cli')).toBe('more');
  });
});
