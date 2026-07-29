/**
 * Open a workspace file with the OS default app (HTML → system browser).
 * Uses Tauri `clutch_open_path`; no new npm dependency.
 */
import { invoke, isTauri } from '@tauri-apps/api/core';

export function isHtmlWorkspacePath(path: string): boolean {
  return /\.html?$/i.test(path.trim());
}

/** Join workspace root + relative path → absolute OS path. */
export function absoluteWorkspacePath(
  workspaceRoot: string | undefined | null,
  relativePath: string,
): string | null {
  const root = (workspaceRoot || '').trim();
  const rel = relativePath.trim().replace(/^[\\/]+/, '');
  if (!root || !rel) return null;
  if (/^(?:[A-Za-z]:[\\/]|\\\\|\/)/.test(rel)) {
    return rel;
  }
  const sep = root.includes('\\') && !root.includes('/') ? '\\' : '/';
  const base = root.replace(/[\\/]+$/, '');
  return `${base}${sep}${rel.replace(/[\\/]+/g, sep)}`;
}

export async function openPathInSystem(absolutePath: string): Promise<void> {
  const path = absolutePath.trim();
  if (!path) throw new Error('empty path');
  if (isTauri()) {
    await invoke('clutch_open_path', { path });
    return;
  }
  // Web/dev fallback — browsers often block file://; still attempt.
  const href = path.startsWith('file:')
    ? path
    : `file://${path.startsWith('/') ? '' : '/'}${path}`;
  const opened = window.open(href, '_blank', 'noopener,noreferrer');
  if (!opened) {
    throw new Error('Could not open in browser (blocked or unsupported)');
  }
}
