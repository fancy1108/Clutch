import { test, expect } from '../../fixtures/desktop.js';
import { authorizeSandboxWorkspace } from '../../helpers/tauri.js';
import { seedPlainChatSession } from '../../helpers/seed.js';
import { waitForRunUsage } from '../../helpers/sidecar.js';

test.describe.configure({ mode: 'serial' });

test('desktop: Overview meters show session tokens after chat', async ({ tauriPage: page }) => {
  await page.waitForSelector('[data-testid="nav-new-chat"]', 30_000);
  await authorizeSandboxWorkspace(page);

  const runId = `run_ui_usage_${Date.now().toString(36)}`;
  const seedText = 'overview usage e2e seed';

  await seedPlainChatSession(runId, seedText);
  const usage = await waitForRunUsage(runId);
  expect(usage.session_tokens).toBeGreaterThan(0);
  expect(usage.token_input).toBeGreaterThan(0);
  expect(usage.token_output).toBeGreaterThan(0);

  await page.click('[data-testid="nav-new-chat"]');
  await page.waitForSelector(`[data-testid="sidebar-session-${runId}"]`, 30_000);
  await page.click(`[data-testid="sidebar-session-${runId}"]`);

  await page.waitForFunction(
    `document.body.innerText.includes(${JSON.stringify(seedText)})`,
    20_000,
  );

  await page.evaluate(`
    (function() {
      const tab = document.querySelector('[data-testid="right-tab-overview"]');
      if (tab && tab.getClientRects().length === 0) {
        document.querySelector('[data-testid="right-panel-toggle"]')?.click();
      }
      document.querySelector('[data-testid="right-tab-overview"]')?.click();
    })()
  `);

  await page.waitForFunction(
    `(() => {
      const el = document.querySelector('[data-testid="overview-token-total"]');
      if (!el || el.getClientRects().length === 0) return false;
      const t = (el.textContent || '').trim();
      return t !== '—' && /\\d/.test(t);
    })()`,
    20_000,
  );

  const meters = (await page.evaluate(`
    (function() {
      const text = (id) => (document.querySelector('[data-testid="' + id + '"]')?.textContent || '').trim();
      return {
        total: text('overview-token-total'),
        input: text('overview-token-input'),
        output: text('overview-token-output'),
        cost: text('overview-token-cost'),
      };
    })()
  `)) as { total: string; input: string; output: string; cost: string };

  expect(meters.total).toMatch(/\d/);
  expect(meters.total).not.toBe('—');
  expect(meters.input).toMatch(/\d/);
  expect(meters.output).toMatch(/\d/);
  expect(meters.cost).toBe('—');
  if (usage.usage_estimated === false) {
    expect(meters.total.startsWith('~')).toBe(false);
  }
});
