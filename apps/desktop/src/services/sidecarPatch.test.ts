import { describe, expect, it } from 'vitest';
import { semverGte } from './sidecarPatch';

describe('sidecarPatch semverGte', () => {
  it('treats equal versions as eligible', () => {
    expect(semverGte('1.2.1', '1.2.1')).toBe(true);
  });

  it('accepts newer app versions against min_app_version', () => {
    expect(semverGte('1.3.0', '1.2.1')).toBe(true);
    expect(semverGte('1.2.0', '1.2.1')).toBe(false);
  });
});
