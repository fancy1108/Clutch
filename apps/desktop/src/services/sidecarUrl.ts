/** Packaged app sidecar listens on 8123; dev sidecar + Vite proxy use 8124. */

export const SIDECAR_PROD_PORT = 8123;
export const SIDECAR_DEV_PORT = 8124;

/** HTTP base: empty in dev (Vite proxies /api → 8124); absolute in production builds. */
export const SIDECAR_BASE = import.meta.env.DEV ? '' : `http://localhost:${SIDECAR_PROD_PORT}`;

export function sidecarHttpUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return SIDECAR_BASE ? `${SIDECAR_BASE}${normalized}` : normalized;
}

export function sidecarWebSocketUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  if (import.meta.env.DEV) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${window.location.host}${normalized}`;
  }
  return `ws://localhost:${SIDECAR_PROD_PORT}${normalized}`;
}
