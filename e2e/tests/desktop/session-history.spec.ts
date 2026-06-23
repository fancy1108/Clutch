import { test, expect } from '../../fixtures/desktop.js';
import { authorizeSandboxWorkspace } from '../../helpers/tauri.js';
import { seedPlainChatSession } from '../../helpers/seed.js';

test.describe.configure({ mode: 'serial' });

test('desktop: sidebar session restores persisted chat after new chat', async ({ tauriPage: page }) => {
  await page.waitForSelector('[data-testid="nav-new-chat"]');
  await authorizeSandboxWorkspace(page);

  const runId = `run_ui_hist_${Date.now().toString(36)}`;
  const seedText = 'sidebar history e2e seed';

  await seedPlainChatSession(runId, seedText);

  // New chat triggers refreshSessions (useEffect on run_id) so seeded session appears in sidebar.
  await page.click('[data-testid="nav-new-chat"]');
  await page.waitForSelector(`[data-testid="sidebar-session-${runId}"]`, 30_000);

  await page.click(`[data-testid="sidebar-session-${runId}"]`);

  await page.waitForFunction(
    `Array.from(document.querySelectorAll('p.whitespace-pre-wrap')).some((p) => p.textContent && p.textContent.includes(${JSON.stringify(seedText)}))`,
    20_000,
  );
});
