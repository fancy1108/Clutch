import type { CliModelsScan } from './cliConfigApi';

type ScanCacheEntry = {
  data: CliModelsScan;
  scannedAt: number;
};

const memoryCache = new Map<string, ScanCacheEntry>();

function storageKey(agentType: string): string {
  return `clutch.cliModelsScan.data.${agentType}`;
}

function todayKey(): string {
  return new Date().toISOString().slice(0, 10);
}

function appBuildKey(): string {
  return import.meta.env.VITE_APP_VERSION ?? import.meta.env.MODE ?? 'dev';
}

function readLocalCache(agentType: string): ScanCacheEntry | null {
  try {
    const raw = localStorage.getItem(storageKey(agentType));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ScanCacheEntry;
    if (!parsed?.data?.agent_type) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function getCachedModelsScan(agentType: string): CliModelsScan | null {
  const memory = memoryCache.get(agentType);
  if (memory) return memory.data;
  const stored = readLocalCache(agentType);
  if (!stored) return null;
  memoryCache.set(agentType, stored);
  return stored.data;
}

export function saveModelsScanCache(agentType: string, data: CliModelsScan): void {
  const entry: ScanCacheEntry = { data, scannedAt: Date.now() };
  memoryCache.set(agentType, entry);
  try {
    localStorage.setItem(storageKey(agentType), JSON.stringify(entry));
  } catch {
    // ignore quota errors
  }
}

export function shouldAutoScanModels(agentType: string): boolean {
  if (!getCachedModelsScan(agentType)) return true;
  const lastDay = localStorage.getItem(`clutch.cliModelsScan.day.${agentType}`);
  const lastBuild = localStorage.getItem(`clutch.cliModelsScan.build.${agentType}`);
  if (lastDay !== todayKey()) return true;
  if (lastBuild !== appBuildKey()) return true;
  return false;
}

export function markModelsAutoScanned(agentType: string): void {
  localStorage.setItem(`clutch.cliModelsScan.day.${agentType}`, todayKey());
  localStorage.setItem(`clutch.cliModelsScan.build.${agentType}`, appBuildKey());
}

export function invalidateModelsScanCache(agentType: string): void {
  memoryCache.delete(agentType);
  localStorage.removeItem(storageKey(agentType));
}
