import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const GCS_ORIGIN = 'https://storage.googleapis.com';

type TauriCsp = Record<string, string>;

type TauriConfig = {
  app: {
    security: {
      csp: TauriCsp;
      devCsp: TauriCsp;
    };
  };
};

function loadTauriConfig(): TauriConfig {
  const configPath = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    '../../src-tauri/tauri.conf.json',
  );
  return JSON.parse(readFileSync(configPath, 'utf8')) as TauriConfig;
}

function directiveIncludesOrigin(directive: string, origin: string): boolean {
  return directive.split(/\s+/).includes(origin);
}

describe('Agnes video CSP', () => {
  const config = loadTauriConfig();

  it.each([
    ['csp', config.app.security.csp],
    ['devCsp', config.app.security.devCsp],
  ] as const)('allows GCS video playback in %s', (_label, csp) => {
    expect(directiveIncludesOrigin(csp['media-src'], GCS_ORIGIN)).toBe(true);
    expect(directiveIncludesOrigin(csp['connect-src'], GCS_ORIGIN)).toBe(true);
  });
});
