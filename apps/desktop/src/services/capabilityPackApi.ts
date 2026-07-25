import { sidecarFetch, sidecarHttpUrl } from './sidecarUrl';

export interface CapabilityPackRecord {
  id: string;
  name: string;
  path?: string;
  skills_mount?: string;
}

export async function fetchCapabilityPacks(): Promise<CapabilityPackRecord[]> {
  const response = await sidecarFetch(sidecarHttpUrl('/api/capability-packs'));
  if (!response.ok) throw new Error(`capability-packs fetch failed (${response.status})`);
  const body = (await response.json()) as { packs: CapabilityPackRecord[] };
  return body.packs ?? [];
}

export async function importCapabilityPack(path: string): Promise<CapabilityPackRecord> {
  const response = await sidecarFetch(sidecarHttpUrl('/api/capability-packs/import'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `import failed (${response.status})`);
  }
  return (await response.json()) as CapabilityPackRecord;
}

export async function uninstallCapabilityPack(packId: string): Promise<void> {
  const response = await sidecarFetch(sidecarHttpUrl('/api/capability-packs/uninstall'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pack_id: packId }),
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string } };
    throw new Error(body.detail?.message ?? `uninstall failed (${response.status})`);
  }
}
