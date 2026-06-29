/** Packaged app sidecar listens on 8123; dev sidecar + Vite proxy use 8124. */

import { invoke } from '@tauri-apps/api/core';

export const SIDECAR_PROD_PORT = 8123;
export const SIDECAR_DEV_PORT = 8124;

/** HTTP base: empty in dev (Vite proxies /api → 8124); absolute in production builds. */
export const SIDECAR_BASE = import.meta.env.DEV ? '' : `http://localhost:${SIDECAR_PROD_PORT}`;

let sidecarTokenPromise: Promise<string | null> | null = null;

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

async function resolveSidecarToken(): Promise<string | null> {
  if (!isTauriRuntime()) {
    return null;
  }
  if (!sidecarTokenPromise) {
    sidecarTokenPromise = invoke<string>('clutch_sidecar_token').catch(() => null);
  }
  return sidecarTokenPromise;
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
  return fetch(input, { ...init, headers });
}

export function sidecarHttpUrl(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return SIDECAR_BASE ? `${SIDECAR_BASE}${normalized}` : normalized;
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
