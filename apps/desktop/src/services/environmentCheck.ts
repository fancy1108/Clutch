/** Welcome-step environment hints (informational; does not gate onboarding). */

import { invoke, isTauri } from '@tauri-apps/api/core';

export type EnvRequirementId = 'os' | 'arch' | 'disk' | 'network' | 'installer';
export type EnvCheckTier = 'ok' | 'warn' | 'info';

export interface EnvRequirementResult {
  id: EnvRequirementId;
  tier: EnvCheckTier;
}

const DISK_MIN_BYTES = 500 * 1024 * 1024;

export function isMacPlatform(userAgent: string): boolean {
  return /Mac|Macintosh/i.test(userAgent);
}

export function isWindowsPlatform(userAgent: string): boolean {
  return /Windows NT/i.test(userAgent);
}

export function parseMacOsMajorFromUa(userAgent: string): number | null {
  const match = userAgent.match(/Mac OS X (\d+)[_.](\d+)/i);
  if (!match) return null;
  const major = Number.parseInt(match[1] ?? '', 10);
  const minor = Number.parseInt(match[2] ?? '', 10);
  if (Number.isNaN(major) || Number.isNaN(minor)) return null;
  // Frozen WKWebView UA reports 10_15 for recent macOS — treat as unknown.
  if (major === 10 && minor >= 15) return null;
  if (major >= 11) return major;
  if (major === 10 && minor >= 14) return 14;
  return major;
}

export function tierForOs(major: number | null, onMac: boolean, onWindows: boolean): EnvCheckTier {
  if (onWindows) return 'ok';
  if (!onMac) return 'warn';
  if (major === null) return 'info';
  return major >= 14 ? 'ok' : 'warn';
}

export function isAppleSiliconArch(architecture: string | null | undefined): boolean {
  const arch = architecture?.toLowerCase() ?? '';
  return arch.includes('arm') || arch.includes('aarch');
}

export function isIntelArch(architecture: string | null | undefined): boolean {
  const arch = architecture?.toLowerCase() ?? '';
  return arch === 'x86_64' || arch === 'x86' || arch.includes('intel');
}

/** Never infer Intel from UA — Apple Silicon Macs report a frozen "Intel Mac" string in WKWebView. */
export function tierForArch(architecture: string | null, onMac: boolean): EnvCheckTier {
  if (!onMac) return 'info';
  if (isAppleSiliconArch(architecture)) return 'ok';
  if (isIntelArch(architecture)) return 'warn';
  return 'info';
}

export function tierForDiskEstimate(quota: number | undefined, usage: number | undefined): EnvCheckTier {
  if (quota === undefined || usage === undefined || quota <= 0) return 'info';
  const free = quota - usage;
  return free >= DISK_MIN_BYTES ? 'ok' : 'warn';
}

export function tierForInstaller(inApp: boolean): EnvCheckTier {
  return inApp ? 'ok' : 'info';
}

async function readNativeCpuArch(): Promise<string | null> {
  if (!isTauri()) return null;
  try {
    const arch = await invoke<string>('clutch_cpu_arch');
    return arch?.trim() || null;
  } catch {
    return null;
  }
}

async function readPlatformHints(): Promise<{ platformVersion: string | null; architecture: string | null }> {
  const data = navigator.userAgentData;
  if (!data?.getHighEntropyValues) {
    return { platformVersion: null, architecture: null };
  }
  try {
    const hints = await data.getHighEntropyValues(['platformVersion', 'architecture']);
    return {
      platformVersion: hints.platformVersion ?? null,
      architecture: hints.architecture ?? null,
    };
  } catch {
    return { platformVersion: null, architecture: null };
  }
}

async function probeInternet(): Promise<boolean> {
  if (!navigator.onLine) return false;
  try {
    await fetch('https://connectivitycheck.gstatic.com/generate_204', {
      method: 'GET',
      cache: 'no-store',
      mode: 'no-cors',
      signal: AbortSignal.timeout(4000),
    });
    return true;
  } catch {
    return false;
  }
}

export async function runEnvironmentChecks(inApp: boolean): Promise<EnvRequirementResult[]> {
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : '';
  const onMac = isMacPlatform(ua);
  const onWindows = isWindowsPlatform(ua);

  let macMajor: number | null = parseMacOsMajorFromUa(ua);
  let architecture: string | null = await readNativeCpuArch();

  if (!architecture && typeof navigator !== 'undefined') {
    const hints = await readPlatformHints();
    const parts = (hints.platformVersion ?? '').split('.');
    const parsed = Number.parseInt(parts[0] ?? '', 10);
    if (!Number.isNaN(parsed)) macMajor = parsed;
    architecture = hints.architecture;
  }

  let diskTier: EnvCheckTier = 'info';
  if (typeof navigator !== 'undefined' && navigator.storage?.estimate) {
    try {
      const estimate = await navigator.storage.estimate();
      diskTier = tierForDiskEstimate(estimate.quota, estimate.usage);
    } catch {
      diskTier = 'info';
    }
  }

  const online = await probeInternet();

  return [
    { id: 'os', tier: tierForOs(macMajor, onMac, onWindows) },
    { id: 'arch', tier: tierForArch(architecture, onMac) },
    { id: 'disk', tier: diskTier },
    { id: 'network', tier: online ? 'ok' : 'warn' },
    { id: 'installer', tier: tierForInstaller(inApp) },
  ];
}
