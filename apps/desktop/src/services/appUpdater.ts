import { isTauri } from '@tauri-apps/api/core';
import { check, type DownloadEvent, type Update } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';

export type AppUpdatePhase = 'idle' | 'available' | 'downloading' | 'ready';

export type AppUpdateProgress = {
  downloadedBytes: number;
  totalBytes?: number;
};

const DISMISS_KEY = 'clutch_update_dismissed_version';

function isDismissed(version: string): boolean {
  try {
    return localStorage.getItem(DISMISS_KEY) === version;
  } catch {
    return false;
  }
}

export function dismissAppUpdate(version: string): void {
  try {
    localStorage.setItem(DISMISS_KEY, version);
  } catch {
    /* ignore quota errors */
  }
}

export function shouldCheckForAppUpdates(): boolean {
  return isTauri() && import.meta.env.PROD;
}

export async function fetchAppUpdate(): Promise<Update | null> {
  if (!shouldCheckForAppUpdates()) return null;
  try {
    const update = await check();
    if (!update || isDismissed(update.version)) {
      await update?.close();
      return null;
    }
    return update;
  } catch (err) {
    // Prep / no latest.json yet: fail silently until OSR-20 go-live (docs/UPDATES.md §0).
    console.warn('[Clutch] Update check failed:', err);
    return null;
  }
}

export async function downloadAppUpdate(
  update: Update,
  onProgress: (progress: AppUpdateProgress) => void,
): Promise<void> {
  let downloadedBytes = 0;
  let totalBytes: number | undefined;

  await update.download((event: DownloadEvent) => {
    if (event.event === 'Started') {
      totalBytes = event.data.contentLength;
      downloadedBytes = 0;
      onProgress({ downloadedBytes, totalBytes });
      return;
    }
    if (event.event === 'Progress') {
      downloadedBytes += event.data.chunkLength;
      onProgress({ downloadedBytes, totalBytes });
    }
  });
}

export async function installAppUpdate(update: Update): Promise<void> {
  await update.install();
  await update.close();
  await relaunch();
}
