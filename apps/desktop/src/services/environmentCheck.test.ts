import { describe, expect, it } from 'vitest';

import {
  isAppleSiliconArch,
  isIntelArch,
  isMacPlatform,
  isX64Arch,
  isWindowsPlatform,
  parseMacOsMajorFromUa,
  tierForArch,
  tierForDiskEstimate,
  tierForInstaller,
  tierForNetwork,
  tierForOs,
} from './environmentCheck';

describe('environmentCheck', () => {
  it('detects mac platform', () => {
    expect(isMacPlatform('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')).toBe(true);
    expect(isMacPlatform('Mozilla/5.0 (Windows NT 10.0)')).toBe(false);
  });

  it('detects Windows platform', () => {
    expect(isWindowsPlatform('Mozilla/5.0 (Windows NT 10.0; Win64; x64)')).toBe(true);
    expect(isWindowsPlatform('Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5)')).toBe(false);
  });

  it('parses macOS major from UA when present', () => {
    expect(parseMacOsMajorFromUa('Mac OS X 14_5')).toBe(14);
    expect(parseMacOsMajorFromUa('Mac OS X 10_15_7')).toBe(null);
  });

  it('tiers supported operating systems', () => {
    expect(tierForOs(14, true, false)).toBe('ok');
    expect(tierForOs(13, true, false)).toBe('warn');
    expect(tierForOs(null, true, false)).toBe('info');
    expect(tierForOs(null, false, true)).toBe('ok');
    expect(tierForOs(14, false, false)).toBe('warn');
  });

  it('detects cpu arch tokens', () => {
    expect(isAppleSiliconArch('aarch64')).toBe(true);
    expect(isAppleSiliconArch('arm64')).toBe(true);
    expect(isIntelArch('x86_64')).toBe(true);
    expect(isX64Arch('x86_64')).toBe(true);
    expect(isX64Arch('x64')).toBe(true);
    expect(isX64Arch('amd64')).toBe(true);
  });

  it('does not treat frozen Intel Mac UA as Intel hardware', () => {
    const frozenUa = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)';
    expect(tierForArch(null, isMacPlatform(frozenUa), false)).toBe('info');
    expect(tierForArch('aarch64', isMacPlatform(frozenUa), false)).toBe('ok');
    expect(tierForArch('x86_64', isMacPlatform(frozenUa), false)).toBe('warn');
  });

  it('tiers Windows package architecture', () => {
    expect(tierForArch('x86_64', false, true)).toBe('ok');
    expect(tierForArch('x64', false, true)).toBe('ok');
    expect(tierForArch('aarch64', false, true)).toBe('info');
    expect(tierForArch('ia32', false, true)).toBe('warn');
    expect(tierForArch(null, false, true)).toBe('info');
  });

  it('tiers disk estimate', () => {
    const gb = 1024 * 1024 * 1024;
    expect(tierForDiskEstimate(2 * gb, 0)).toBe('ok');
    expect(tierForDiskEstimate(400 * 1024 * 1024, 0)).toBe('warn');
    expect(tierForDiskEstimate(undefined, undefined)).toBe('info');
  });

  it('tiers installer advisory', () => {
    expect(tierForInstaller(true)).toBe('ok');
    expect(tierForInstaller(false)).toBe('info');
  });

  it('tiers network probes without over-warning captive or blocked probes', () => {
    expect(tierForNetwork(false, null)).toBe('warn');
    expect(tierForNetwork(true, true)).toBe('ok');
    expect(tierForNetwork(true, null)).toBe('info');
  });
});
