import { test, expect, sandboxRoot } from '../../fixtures/desktop.js';
import { authorizeSandboxWorkspace, delay } from '../../helpers/tauri.js';
import { startVideoProductionRun } from '../../helpers/workflow.js';

test.describe.configure({ mode: 'serial' });

async function openSettings(page: {
  click: (selector: string) => Promise<void>;
  locator: (selector: string) => { toBeVisible: () => Promise<void> };
}) {
  await page.click('[data-testid="nav-settings"]');
  await expect(page.locator('[data-testid="settings-nav-general"]')).toBeVisible();
}

test('desktop: full UI coverage with sandbox isolation', async ({ tauriPage: page }) => {
  await test.step('G-01 sidebar toggle', async () => {
    await page.waitForSelector('[data-testid="nav-new-chat"]');
    await page.click('[data-testid="sidebar-toggle"]');
    await page.click('[data-testid="sidebar-toggle"]');
  });

  await test.step('S-05 authorize sandbox workspace', async () => {
    await authorizeSandboxWorkspace(page);
  });

  await test.step('P-01..P-08 settings navigation', async () => {
    await openSettings(page);
    for (const id of [
      'settings-nav-general',
      'settings-nav-tools',
      'settings-nav-agents',
      'settings-nav-workflows',
      'settings-nav-models',
      'settings-nav-skills',
      'settings-nav-mcp',
      'settings-nav-appearance',
    ]) {
      await page.click(`[data-testid="${id}"]`);
      await delay(300);
    }
    await page.click('[data-testid="settings-close"]');
  });

  await test.step('S-02/S-03 sidebar views', async () => {
    await page.click('[data-testid="nav-agents"]');
    await page.click('[data-testid="nav-workflows"]');
    await expect(page.locator('[data-testid="workflow-item-video-production"]')).toBeVisible();
    await page.click('[data-testid="nav-new-chat"]');
  });

  await test.step('W-01/W-10 run Video Production in chat', async () => {
    await page.click('[data-testid="nav-workflows"]');
    await page.click('[data-testid="workflow-item-video-production"]');
    await page.click('[data-testid="workflow-run-in-chat"]');
    await page.waitForSelector('[data-testid="chat-input"]');

    const runId = await startVideoProductionRun('e2e orchestration smoke');
    await page.click('[data-testid="nav-new-chat"]');
    await page.waitForSelector(`[data-testid="sidebar-session-${runId}"]`, 30_000);
    await page.click(`[data-testid="sidebar-session-${runId}"]`);
    await page.waitForSelector('[data-testid="chat-approve"]', 60_000);
  });

  await test.step('R-06..R-08 right panel tabs', async () => {
    for (const tab of ['overview', 'files', 'flow', 'changes', 'terminal']) {
      await page.click(`[data-testid="right-tab-${tab}"]`);
    }
  });

  await test.step('C-07 approve human gate', async () => {
    await page.click('[data-testid="chat-approve"]');
    await page.waitForFunction(
      '(() => { const text = document.body.innerText.toLowerCase(); return text.includes("passed") || text.includes("idle"); })()',
      30_000,
    );
  });

  await test.step('R-09 terminal clear', async () => {
    await page.click('[data-testid="right-tab-terminal"]');
    await page.click('[data-testid="terminal-clear-btn"]');
  });

  await test.step('G-09 branch menu', async () => {
    const gitInfo = (await page.evaluate(`
      (async function() {
        const res = await fetch('http://127.0.0.1:8123/api/workspace/git');
        if (!res.ok) return { is_git_repo: false, branch: null, branches: [] };
        return res.json();
      })()
    `)) as { is_git_repo: boolean; branch: string | null; branches: string[] };

    await page.click('[data-testid="footer-branch-trigger"]');
    await expect(page.locator('[data-testid="footer-branch-menu"]')).toBeVisible();

    if (gitInfo.is_git_repo && gitInfo.branch) {
      await expect(page.locator('[data-testid="footer-branch-trigger"]')).toContainText(gitInfo.branch);
      await expect(page.locator(`[data-testid="footer-branch-item-${gitInfo.branch}"]`)).toBeVisible();
    }

    await page.click('[data-testid="footer-branch-trigger"]');
  });

  await test.step('G-07/G-08 footer shortcuts', async () => {
    await page.click('[data-testid="footer-model-trigger"]');
    await expect(page.locator('[data-testid="settings-nav-models"]')).toBeVisible();
    await page.click('[data-testid="settings-close"]');
    await page.click('[data-testid="footer-workflow-trigger"]');
    await page.click('[data-testid="nav-new-chat"]');
  });

  await test.step('G-03 language switch', async () => {
    await page.click('[data-testid="nav-new-chat"]');
    await page.click('[data-testid="lang-zh"]');
    await expect(page.locator('[data-testid="chat-supervised-title"]')).toContainText('开始新的监督会话');
    await page.click('[data-testid="lang-en"]');
    await expect(page.locator('[data-testid="chat-supervised-title"]')).toContainText('Start a supervised session');
  });

  await test.step('G-02 right panel toggle', async () => {
    await page.click('[data-testid="right-panel-toggle"]');
    await page.click('[data-testid="right-panel-toggle"]');
  });

  await test.step('sandbox path guard', async () => {
    const workspacePath = (await page.evaluate(`
      (async function() {
        const res = await fetch('http://127.0.0.1:8123/api/workspace');
        if (!res.ok) return '';
        const body = await res.json();
        return body.workspace_path ?? '';
      })()
    `)) as string;
    expect(workspacePath.includes(sandboxRoot) || workspacePath.includes('clutch-e2e')).toBeTruthy();
    expect(workspacePath).toContain('sandbox-project');
  });
});

test('desktop: reject placeholder stub strings in UI', async ({ tauriPage: page }) => {
  await page.waitForSelector('[data-testid="nav-new-chat"]');
  const leaked = (await page.evaluate(`
    (function() {
      const forbidden = ['Simulated action', 'Terminal clears and restarts', 'mockData', 'Vibe coding workspace'];
      return forbidden.filter((snippet) => document.body.innerText.includes(snippet));
    })()
  `)) as string[];
  expect(leaked).toEqual([]);
});
