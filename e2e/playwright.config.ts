import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 180_000,
  expect: { timeout: 15_000 },
  workers: 1,
  retries: 0,
  projects: [
    {
      name: 'api',
      testMatch: /tests\/(smoke|mvp-closed-loop|session-history|i18n|workspace-git)\.spec\.ts/,
      use: { baseURL: 'http://127.0.0.1:8123' },
    },
    {
      name: 'hybrid-api',
      testMatch: /tests\/hybrid-concurrent-sessions\.spec\.ts/,
      use: { baseURL: 'http://127.0.0.1:8123' },
    },
    {
      name: 'desktop',
      testMatch: /tests\/desktop\/.*\.spec\.ts/,
      use: { mode: 'tauri' },
    },
  ],
});
