/** Packaged app sidecar listens on 8123; dev sidecar + Vite proxy use 8124. */

import { invoke, isTauri } from '@tauri-apps/api/core';

export const SIDECAR_PROD_PORT = 8123;
export const SIDECAR_DEV_PORT = 8124;

/** HTTP base: empty in dev (Vite proxies /api → 8124); absolute in production builds. */
export const SIDECAR_BASE = import.meta.env.DEV ? '' : `http://localhost:${SIDECAR_PROD_PORT}`;

let cachedSidecarToken: string | null | undefined;

async function resolveSidecarToken(force = false): Promise<string | null> {
  if (!isTauri()) {
    return null;
  }
  if (!force && cachedSidecarToken !== undefined) {
    return cachedSidecarToken;
  }
  try {
    const token = (await invoke<string>('clutch_sidecar_token')).trim();
    cachedSidecarToken = token || null;
    return cachedSidecarToken;
  } catch {
    if (!force) {
      cachedSidecarToken = undefined;
    }
    return null;
  }
}

export function resetSidecarTokenCache(): void {
  cachedSidecarToken = undefined;
}

export async function sidecarAuthHeaders(init?: HeadersInit): Promise<Headers> {
  const headers = new Headers(init);
  const token = await resolveSidecarToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return headers;
}

/** Authenticated fetch for Sidecar HTTP APIs (OSR-08). */
export async function sidecarFetch(input: string, init?: RequestInit): Promise<Response> {
  const headers = await sidecarAuthHeaders(init?.headers);
  let response = await fetch(input, { ...init, headers });
  if (response.status === 401 && isTauri()) {
    resetSidecarTokenCache();
    const retryHeaders = await sidecarAuthHeaders(init?.headers);
    response = await fetch(input, { ...init, headers: retryHeaders });
  }
  return response;
}

export function sidecarHttpUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return SIDECAR_BASE ? `${SIDECAR_BASE}${normalized}` : normalized;
}

/** True when src targets Sidecar HTTP (relative /api or loopback sidecar port). */
export function isSidecarApiPath(src: string): boolean {
  const trimmed = src.trim();
  if (trimmed.startsWith('/api/')) {
    return true;
  }
  try {
    const url = new URL(trimmed);
    if (url.hostname !== 'localhost' && url.hostname !== '127.0.0.1') {
      return false;
    }
    const port = url.port || (url.protocol === 'https:' ? '443' : '80');
    return port === String(SIDECAR_PROD_PORT) || port === String(SIDECAR_DEV_PORT);
  } catch {
    return false;
  }
}

/** Append session token for media elements that cannot send Authorization headers. */
export async function sidecarAuthedHttpUrl(path: string): Promise<string> {
  const trimmed = path.trim();
  let resolved = trimmed;
  if (trimmed.startsWith('/api/')) {
    resolved = sidecarHttpUrl(trimmed);
  } else if (!trimmed.startsWith('http')) {
    resolved = sidecarHttpUrl(trimmed);
  }
  const token = await resolveSidecarToken();
  if (!token) {
    return resolved;
  }
  const joiner = resolved.includes('?') ? '&' : '?';
  return `${resolved}${joiner}token=${encodeURIComponent(token)}`;
}

export async function sidecarWebSocketUrl(path: string): Promise<string> {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  let base: string;
  if (import.meta.env.DEV) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    base = `${proto}//${window.location.host}${normalized}`;
  } else {
    base = `ws://localhost:${SIDECAR_PROD_PORT}${normalized}`;
  }
  const token = await resolveSidecarToken();
  if (!token) {
    return base;
  }
  const joiner = base.includes('?') ? '&' : '?';
  return `${base}${joiner}token=${encodeURIComponent(token)}`;
}
