import { describe, expect, it } from 'vitest';

import {
  isAppleSiliconArch,
  isIntelArch,
  isMacPlatform,
  parseMacOsMajorFromUa,
  tierForArch,
  tierForDiskEstimate,
  tierForGatekeeper,
  tierForMacOs,
} from './environmentCheck';

describe('environmentCheck', () => {
  it('detects mac platform', () => {
    expect(isMacPlatform('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')).toBe(true);
    expect(isMacPlatform('Mozilla/5.0 (Windows NT 10.0)')).toBe(false);
  });

  it('parses macOS major from UA when present', () => {
    expect(parseMacOsMajorFromUa('Mac OS X 14_5')).toBe(14);
    expect(parseMacOsMajorFromUa('Mac OS X 10_15_7')).toBe(null);
  });

  it('tiers macOS version', () => {
    expect(tierForMacOs(14, true)).toBe('ok');
    expect(tierForMacOs(13, true)).toBe('warn');
    expect(tierForMacOs(null, true)).toBe('info');
    expect(tierForMacOs(14, false)).toBe('warn');
  });

  it('detects cpu arch tokens', () => {
    expect(isAppleSiliconArch('aarch64')).toBe(true);
    expect(isAppleSiliconArch('arm64')).toBe(true);
    expect(isIntelArch('x86_64')).toBe(true);
  });

  it('does not treat frozen Intel Mac UA as Intel hardware', () => {
    const frozenUa = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)';
    expect(tierForArch(null, isMacPlatform(frozenUa))).toBe('info');
    expect(tierForArch('aarch64', isMacPlatform(frozenUa))).toBe('ok');
    expect(tierForArch('x86_64', isMacPlatform(frozenUa))).toBe('warn');
  });

  it('tiers disk estimate', () => {
    const gb = 1024 * 1024 * 1024;
    expect(tierForDiskEstimate(2 * gb, 0)).toBe('ok');
    expect(tierForDiskEstimate(400 * 1024 * 1024, 0)).toBe('warn');
    expect(tierForDiskEstimate(undefined, undefined)).toBe('info');
  });

  it('tiers gatekeeper', () => {
    expect(tierForGatekeeper(true)).toBe('ok');
    expect(tierForGatekeeper(false)).toBe('info');
  });
});
