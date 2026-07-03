import { invoke, isTauri } from '@tauri-apps/api/core';
import { useEffect, useState } from 'react';

export type HostOs = 'macos' | 'windows' | 'linux' | string;

let cachedHostOs: HostOs | null = null;

export async function getHostOs(): Promise<HostOs> {
  if (cachedHostOs) return cachedHostOs;
  if (!isTauri()) {
    cachedHostOs = 'web';
    return cachedHostOs;
  }
  cachedHostOs = (await invoke<string>('clutch_host_os')) as HostOs;
  return cachedHostOs;
}

export function isWindowsHost(hostOs: HostOs): boolean {
  return hostOs === 'windows';
}

export function isMacHost(hostOs: HostOs): boolean {
  return hostOs === 'macos';
}

export function useHostOs(): HostOs {
  const [hostOs, setHostOs] = useState<HostOs>(cachedHostOs ?? 'macos');

  useEffect(() => {
    let cancelled = false;
    void getHostOs().then((value) => {
      if (!cancelled) setHostOs(value);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return hostOs;
}
