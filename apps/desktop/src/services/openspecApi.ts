/** OpenSpec CLI integration via Sidecar. */

import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

export interface OpenSpecChange {
  name?: string;
  id?: string;
  status?: string;
  [key: string]: unknown;
}

export interface OpenSpecListResponse {
  available: boolean;
  error?: string;
  changes: OpenSpecChange[];
}

export interface OpenSpecStatusResponse {
  available: boolean;
  error?: string;
  status?: Record<string, unknown>;
}

export async function fetchOpenSpecList(): Promise<OpenSpecListResponse> {
  try {
    const res = await sidecarFetch(`${BASE}/api/openspec/list`);
    if (!res.ok) return { available: false, error: `HTTP ${res.status}`, changes: [] };
    return (await res.json()) as OpenSpecListResponse;
  } catch (err) {
    return { available: false, error: err instanceof Error ? err.message : String(err), changes: [] };
  }
}

export async function fetchOpenSpecStatus(change: string): Promise<OpenSpecStatusResponse> {
  try {
    const res = await sidecarFetch(`${BASE}/api/openspec/status?change=${encodeURIComponent(change)}`);
    if (!res.ok) return { available: false, error: `HTTP ${res.status}` };
    return (await res.json()) as OpenSpecStatusResponse;
  } catch (err) {
    return { available: false, error: err instanceof Error ? err.message : String(err) };
  }
}