import { describe, expect, it } from 'vitest';
import { SIDECAR_BASE, sidecarHttpUrl } from './sidecarUrl';

describe('sidecarUrl', () => {
  it('uses relative paths in dev for Vite proxy', () => {
    expect(import.meta.env.DEV).toBe(true);
    expect(SIDECAR_BASE).toBe('');
    expect(sidecarHttpUrl('/api/health')).toBe('/api/health');
  });
});
