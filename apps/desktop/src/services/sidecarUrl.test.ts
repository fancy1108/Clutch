import { describe, expect, it } from 'vitest';
import { SIDECAR_BASE, isSidecarApiPath, sidecarHttpUrl } from './sidecarUrl';

describe('sidecarUrl', () => {
  it('uses relative paths in dev for Vite proxy', () => {
    expect(import.meta.env.DEV).toBe(true);
    expect(SIDECAR_BASE).toBe('');
    expect(sidecarHttpUrl('/api/health')).toBe('/api/health');
  });

  it('detects sidecar API paths', () => {
    expect(isSidecarApiPath('/api/workspace/media?path=x')).toBe(true);
    expect(isSidecarApiPath('http://localhost:8123/api/workspace/media?path=x')).toBe(true);
    expect(isSidecarApiPath('http://localhost:8124/api/workspace/media?path=x')).toBe(true);
    expect(isSidecarApiPath('https://storage.googleapis.com/bucket/v.mp4')).toBe(false);
  });
});
