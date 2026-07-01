import { defineConfig } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const e2eRoot = join(dirname(fileURLToPath(import.meta.url)), '.');
const config = JSON.parse(readFileSync(join(e2eRoot, 'acceptance.config.json'), 'utf8')) as {
  test_timeouts_ms: { default_test: number; suite_global: number };
};

/** Real-connection acceptance — tight per-test + suite caps (see acceptance.config.json). */
export default defineConfig({
  testDir: './tests',
  testMatch: /tests\/desktop\/acceptance\.spec\.ts/,
  timeout: config.test_timeouts_ms.default_test,
  globalTimeout: config.test_timeouts_ms.suite_global,
  expect: { timeout: 10_000 },
  workers: 1,
  retries: 0,
  projects: [
    {
      name: 'desktop',
      testMatch: /acceptance\.spec\.ts/,
      use: { mode: 'tauri' },
    },
  ],
});
