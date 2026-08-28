import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, expect } from '../../fixtures/desktop.js';
import { authorizeSandboxWorkspace, delay, setTextareaValue } from '../../helpers/tauri.js';
import {
  clearWorkflowSelection,
  ensureChatWorkspaceMode,
  selectFooterAgent,
  startNewChat,
} from '../../helpers/chat-ui.js';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');

const CLI_SCANS = [
  'codex-cli',
  'aider-cli',
  'codebuddy-cli',
  'antigravity-cli',
  'rivet-cli',
  'ollama-cli',
  'zcode-cli',
];

async function openSettings(page: {
  click: (s: string) => Promise<void>;
  evaluate: (s: string) => Promise<unknown>;
  waitForSelector: (s: string, t?: number) => Promise<void>;
  locator: (s: string) => { count: () => Promise<number> };
}): Promise<void> {
  if ((await page.locator('[data-testid="footer-workflow-menu"]').count()) > 0) {
    await page.click('[data-testid="footer-workflow-trigger"]');
  }
  if ((await page.locator('[data-testid="footer-model-menu"]').count()) > 0) {
    await page.click('[data-testid="footer-model-trigger"]');
  }
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    await page.evaluate(`document.querySelector('[data-testid="nav-settings"]')?.click()`);
    try {
      await page.waitForSelector('[data-testid="settings-nav-general"]', 2_000);
      return;
    } catch {
      /* retry */
    }
  }
  throw new Error('timeout opening Settings');
}

async function clickId(page: { evaluate: (s: string) => Promise<unknown> }, id: string): Promise<void> {
  await page.evaluate(`document.querySelector('[data-testid="${id}"]')?.click()`);
}

async function openRightOverview(page: { evaluate: (s: string) => Promise<unknown> }): Promise<void> {
  await page.evaluate(`
    (function() {
      const tab = document.querySelector('[data-testid="right-tab-overview"]');
      if (!tab || tab.getClientRects().length === 0) {
        document.querySelector('[data-testid="right-panel-toggle"]')?.click();
      }
      document.querySelector('[data-testid="right-tab-overview"]')?.click();
    })()
  `);
}

test('desktop: FM-01…22 acceptance playbook', async ({ tauriPage: page }) => {
  test.setTimeout(180_000);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  await ensureChatWorkspaceMode(page);
  await clearWorkflowSelection(page);

  await test.step('FM-20/21/22 docs', () => {
    const perf = readFileSync(resolve(repoRoot, 'docs/PERFORMANCE.md'), 'utf8');
    expect(perf).toMatch(/### 1\.1/);
    expect(perf).toContain('测得');
    expect(readFileSync(resolve(repoRoot, 'docs/APPLE_NOTARIZATION.md'), 'utf8').length).toBeGreaterThan(80);
    expect(readFileSync(resolve(repoRoot, 'docs/EXTERNAL_AUDIT.md'), 'utf8').length).toBeGreaterThan(80);
  });

  await test.step('FM-01/02/03/12 Settings', async () => {
    await openSettings(page);
    await expect(page.locator('[data-testid="general-default-workspace"]')).toBeVisible();
    await expect(page.locator('[data-testid="high-risk-confirm-toggle"]')).toBeVisible();
    await expect(page.locator('[data-testid="untrusted-confirm-toggle"]')).toBeVisible();
    await expect(page.locator('[data-testid="general-app-version"]')).toContainText('Clutch v');
    await expect(page.locator('[data-testid="memory-search-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="memory-search-run"]')).toBeVisible();
    await clickId(page, 'settings-nav-tools');
    await expect(page.locator('[data-testid="exec-policy-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid="exec-policy-add"]')).toBeVisible();
    await clickId(page, 'settings-nav-models');
    await expect(page.locator('[data-testid="clutch-current-model"]')).toBeVisible();
    await clickId(page, 'capability-tab-more');
    for (const id of CLI_SCANS) {
      await expect(page.locator(`[data-testid="cli-scan-${id}"]`)).toBeVisible();
    }
    await clickId(page, 'cli-scan-codex-cli');
    await expect(page.locator('[data-testid="cli-models-scan-codex-cli"]')).toBeVisible();
    await expect(page.locator('[data-testid="cli-scan-rescan"]')).toBeVisible();
    await clickId(page, 'settings-close');
  });

  await test.step('FM-09 dispatch banner', async () => {
    await startNewChat(page);
    await expect(page.locator('[data-testid="dispatch-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="dispatch-banner"]')).toContainText(/current Agent|当前 Agent/i);
  });

  await test.step('FM-10 assigned agent engine', async () => {
    await clickId(page, 'nav-workflows');
    await page.waitForSelector('[data-testid="workflow-create"]', 10_000);
    await delay(800);
    await page.evaluate(`
      (function() {
        const add = document.querySelector('[data-testid="workflow-add-node"]')
          || Array.from(document.querySelectorAll('button')).find((b) => /Add Node|添加节点/.test(b.textContent || ''));
        if (!add) throw new Error('Add Node not found');
        add.click();
      })()
    `);
    await delay(200);
    await page.evaluate(`
      (function() {
        const agent = document.querySelector('[data-testid="workflow-add-node-agent_task"]')
          || Array.from(document.querySelectorAll('button')).find((b) => /Agent Node/.test(b.textContent || ''));
        if (!agent) throw new Error('Agent Node not found');
        agent.click();
      })()
    `);
    await page.waitForSelector('[data-testid="node-agent-select"]', 10_000);
    await expect(page.locator('[data-testid="node-tool-select"]')).toHaveCount(0);
    await clickId(page, 'settings-close');
    await startNewChat(page);
    await ensureChatWorkspaceMode(page);
    await clearWorkflowSelection(page);
  });

  await test.step('FM-11 worktree enable then discard', async () => {
    expect(await page.locator('[data-testid="add-parallel-worktree"]').count()).toBe(0);
    await clickId(page, 'composer-plus');
    await page.waitForSelector('[data-testid="enable-worktree"]', 5_000);
    await clickId(page, 'enable-worktree');
    await page.waitForSelector('[data-testid="worktree-active-chip"]', 15_000);
    await clickId(page, 'footer-worktree-trigger');
    await expect(page.locator('[data-testid="add-parallel-worktree"]')).toBeVisible();
    await clickId(page, 'discard-worktree');
    await page.waitForFunction(
      `(() => !document.querySelector('[data-testid="worktree-active-chip"]'))()`,
      15_000,
    );
  });

  await test.step('FM-06/07 orchestra', async () => {
    await selectFooterAgent(page, 'agent-e2e-hybrid');
    await page.waitForSelector('[data-testid="workspace-view-terminal"]', 15_000);
    await clickId(page, 'workspace-view-terminal');
    await page.waitForSelector('[data-testid="orchestrator-bar"]', 15_000);
    await setTextareaValue(page, '[data-testid="orchestrator-input"]', '@Claude E2E Hybrid ping');
    await clickId(page, 'orchestrator-send-btn');
    await page.waitForSelector('[data-testid="dispatch-confirm-card"]', 15_000);
    await page.click('[data-testid="confirm-dispatch-btn"]');
    await openRightOverview(page);
    await page.waitForSelector('[data-testid="overview-dispatch-log"]', 15_000);
    await expect(page.locator('[data-testid="save-dispatch-as-workflow"]')).toBeVisible();
    await ensureChatWorkspaceMode(page);
  });

  await test.step('FM-16 Design entry', async () => {
    await clickId(page, 'mode-design');
    await page.waitForSelector('[data-testid="design-workspace"]', 10_000);
    await clickId(page, 'mode-coding');
    await page.waitForSelector('[data-testid="chat-input"]', 10_000);
  });

  await test.step('FM-18 validation strip (skip if no failed run)', async () => {
    await openRightOverview(page);
    if ((await page.locator('[data-testid="validation-failure-strip"]').count()) > 0) {
      await expect(page.locator('[data-testid="validation-failure-strip"]')).toBeVisible();
    }
  });
});
