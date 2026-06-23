import { createTauriTest } from '../node_modules/@srsholmes/tauri-playwright/dist/index.js';

const sandboxRoot = process.env.CLUTCH_E2E_SANDBOX ?? '';
if (!sandboxRoot) {
  throw new Error('CLUTCH_E2E_SANDBOX must be set before desktop E2E');
}

export const { test, expect } = createTauriTest({
  devUrl: 'http://localhost:3000',
  mcpSocket: '/tmp/clutch-tauri-playwright.sock',
});

export { sandboxRoot };
