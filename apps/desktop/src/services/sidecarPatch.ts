import { invoke, isTauri } from '@tauri-apps/api/core';
import { getVersion } from '@tauri-apps/api/app';
import { isHotpatchSuppressed } from './appUpdater';

const MANIFEST_URL =
  'https://github.com/fancy1108/Clutch/releases/latest/download/sidecar-patch.json';

export type SidecarPatchManifest = {
  patch_id: string;
  min_app_version?: string;
  max_app_version?: string;
  platforms: Record<string, { url: string; sha256: string }>;
  notes?: string;
  severity?: 'normal' | 'major' | 'critical';
};

function parseSemver(v: string): number[] {
  return v
    .replace(/^v/i, '')
    .split('.')
    .map((p) => Number.parseInt(p.replace(/[^0-9].*$/, ''), 10) || 0);
}

/** Returns true if `a` >= `b` (semver-ish). */
export function semverGte(a: string, b: string): boolean {
  const aa = parseSemver(a);
  const bb = parseSemver(b);
  const n = Math.max(aa.length, bb.length);
  for (let i = 0; i < n; i++) {
    const x = aa[i] ?? 0;
    const y = bb[i] ?? 0;
    if (x > y) return true;
    if (x < y) return false;
  }
  return true;
}

export function shouldCheckSidecarPatch(): boolean {
  return isTauri() && import.meta.env.PROD;
}

export async function fetchSidecarPatchManifest(): Promise<SidecarPatchManifest | null> {
  try {
    const res = await fetch(MANIFEST_URL, { cache: 'no-store' });
    if (!res.ok) return null;
    return (await res.json()) as SidecarPatchManifest;
  } catch {
    return null;
  }
}

async function platformKey(): Promise<string | null> {
  try {
    const [os, arch] = await Promise.all([
      invoke<string>('clutch_host_os'),
      invoke<string>('clutch_cpu_arch'),
    ]);
    if (os === 'macos') return `darwin-${arch}`;
    return null;
  } catch {
    return null;
  }
}

export async function installedSidecarPatchId(): Promise<string | null> {
  try {
    return await invoke<string | null>('clutch_sidecar_patch_status');
  } catch {
    return null;
  }
}

export async function pendingSidecarPatchId(): Promise<string | null> {
  try {
    return await invoke<string | null>('clutch_sidecar_patch_pending');
  } catch {
    return null;
  }
}

export async function downloadSidecarPatch(
  url: string,
  patchId: string,
  sha256: string,
): Promise<void> {
  await invoke('clutch_download_sidecar_patch', {
    url,
    patchId,
    sha256,
  });
}

export async function applySidecarPatch(): Promise<void> {
  await invoke('clutch_apply_sidecar_patch');
}

/**
 * Silent check: if a newer applicable patch exists, download it.
 * Returns patch_id when ready to apply (needs sidecar restart).
 */
export async function checkAndDownloadSidecarPatch(): Promise<string | null> {
  if (!shouldCheckSidecarPatch() || isHotpatchSuppressed()) return null;

  const pending = await pendingSidecarPatchId();
  if (pending) return pending;

  const manifest = await fetchSidecarPatchManifest();
  if (!manifest?.patch_id) return null;

  const appVersion = await getVersion();
  if (manifest.min_app_version && !semverGte(appVersion, manifest.min_app_version)) {
    return null;
  }
  if (manifest.max_app_version && !semverGte(manifest.max_app_version, appVersion)) {
    return null;
  }

  const installed = await installedSidecarPatchId();
  if (installed === manifest.patch_id) return null;

  const key = await platformKey();
  if (!key) return null;
  const asset = manifest.platforms[key];
  if (!asset?.url || !asset.sha256) return null;

  await downloadSidecarPatch(asset.url, manifest.patch_id, asset.sha256);
  return manifest.patch_id;
}
