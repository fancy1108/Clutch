import { test, expect, sandboxRoot } from '../../fixtures/desktop.js';
import { authorizeSandboxWorkspace, delay } from '../../helpers/tauri.js';
import { clearWorkflowSelection, ensureChatWorkspaceMode } from '../../helpers/chat-ui.js';
import { startVideoProductionRun, ensureE2eUserWorkflow } from '../../helpers/workflow.js';

test.describe.configure({ mode: 'serial' });

async function openSettings(page: {
  click: (selector: string) => Promise<void>;
  evaluate: (script: string) => Promise<unknown>;
  waitForSelector: (selector: string, timeout?: number) => Promise<void>;
  locator: (selector: string) => { toBeVisible: () => Promise<void>; count: () => Promise<number> };
}) {
  // Close leftover footer menus that can intercept the Settings click.
  if ((await page.locator('[data-testid="footer-workflow-menu"]').count()) > 0) {
    await page.click('[data-testid="footer-workflow-trigger"]');
  }
  if ((await page.locator('[data-testid="footer-model-menu"]').count()) > 0) {
    await page.click('[data-testid="footer-model-trigger"]');
  }
  // DOM .click() bypasses overlay hit-testing that sometimes blocks tauri-playwright click.
  // Retry: New Chat's async discard can still setView('chat') and close the modal.
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    await page.evaluate(`
      (function() {
        const el = document.querySelector('[data-testid="nav-settings"]');
        if (!el) throw new Error('nav-settings not in DOM');
        el.click();
      })()
    `);
    const remaining = Math.max(250, deadline - Date.now());
    try {
      await page.waitForSelector('[data-testid="settings-nav-general"]', Math.min(2_000, remaining));
      return;
    } catch {
      // Modal closed by a racing setView('chat'); click Settings again.
    }
  }
  throw new Error('timeout waiting for [data-testid="settings-nav-general"]');
}

test('desktop: full UI coverage with sandbox isolation', async ({ tauriPage: page }) => {
  await test.step('G-01 sidebar toggle', async () => {
    await page.waitForSelector('[data-testid="nav-new-chat"]');
    await page.click('[data-testid="workspace-sidebar-toggle"]');
    await page.click('[data-testid="workspace-sidebar-toggle"]');
  });

  await test.step('S-05 authorize sandbox workspace', async () => {
    await authorizeSandboxWorkspace(page);
  });

  await test.step('P-01..P-08 settings navigation', async () => {
    await openSettings(page);
    await expect(page.locator('[data-testid="event-channel-test"]')).toBeVisible();
    await expect(page.locator('[data-testid="memory-search-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="general-default-workspace"]')).toBeVisible();
    await expect(page.locator('[data-testid="high-risk-confirm-toggle"]')).toBeVisible();
    await expect(page.locator('[data-testid="untrusted-confirm-toggle"]')).toBeVisible();
    await expect(page.locator('[data-testid="general-app-version"]')).toContainText('Clutch v');
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
    await page.click('[data-testid="settings-nav-tools"]');
    await expect(page.locator('[data-testid="exec-policy-panel"]')).toBeVisible();
    await page.click('[data-testid="settings-nav-models"]');
    await expect(page.locator('[data-testid="planner-model-select"]')).toBeVisible();
    await expect(page.locator('[data-testid="executor-model-select"]')).toBeVisible();
    await page.click('[data-testid="capability-tab-more"]');
    await expect(page.locator('[data-testid="cli-scan-codex-cli"]')).toBeVisible();
    await expect(page.locator('[data-testid="cli-scan-aider-cli"]')).toBeVisible();
    await page.click('[data-testid="settings-close"]');
  });

  await test.step('S-02/S-03 sidebar views', async () => {
    await page.click('[data-testid="nav-agents"]');
    await page.click('[data-testid="nav-workflows"]');
    const workflowId = await ensureE2eUserWorkflow();
    await page.click('[data-testid="nav-workflows"]');
    await expect(page.locator(`[data-testid="workflow-item-${workflowId}"]`)).toBeVisible();
    await page.click('[data-testid="nav-new-chat"]');
    await expect(page.locator('[data-testid="dispatch-banner"]')).toBeVisible();
  });

  await test.step('W-01/W-10 run user workflow in chat', async () => {
    const workflowId = await ensureE2eUserWorkflow();
    await page.click('[data-testid="nav-workflows"]');
    await page.click(`[data-testid="workflow-item-${workflowId}"]`);
    await page.click('[data-testid="settings-close"]');
    await page.waitForSelector('[data-testid="chat-input"]');

    const runId = await startVideoProductionRun('e2e orchestration smoke');
    await page.click('[data-testid="nav-new-chat"]');
    await page.waitForSelector(`[data-testid="sidebar-session-${runId}"]`, 30_000);
    await page.click(`[data-testid="sidebar-session-${runId}"]`);
    await page.waitForSelector('[data-testid="chat-approve"]', 60_000);
  });

  await test.step('R-06..R-08 right panel tabs', async () => {
    // Flow tab removed from right panel (workflow steps live in Overview when a SOP is active).
    for (const tab of ['overview', 'files', 'changes', 'terminal']) {
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
        const res = await fetch('/api/workspace/git');
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
    // Leave the video-production session so Model is not workflow-disabled.
    await page.click('[data-testid="nav-new-chat"]');
    await ensureChatWorkspaceMode(page);
    await clearWorkflowSelection(page);
    // Footer Model opens a menu; Settings Models is behind "Manage models...".
    await page.click('[data-testid="footer-model-trigger"]');
    await page.waitForSelector('[data-testid="footer-model-manage"]', 10_000);
    await page.click('[data-testid="footer-model-manage"]');
    await expect(page.locator('[data-testid="settings-nav-models"]')).toBeVisible();
    await page.click('[data-testid="settings-close"]');
    await page.click('[data-testid="footer-workflow-trigger"]');
    await page.waitForSelector('[data-testid="footer-workflow-menu"]', 10_000);
    await page.click('[data-testid="footer-workflow-trigger"]'); // close menu
    await page.click('[data-testid="nav-new-chat"]');
  });

  await test.step('G-03 language switch', async () => {
    await page.click('[data-testid="nav-new-chat"]');
    await delay(1_000);
    await openSettings(page);
    // nav-settings opens General; use DOM click — modal overlays confuse tauri-playwright hit tests.
    await page.evaluate(`document.querySelector('[data-testid="lang-zh"]').click()`);
    await page.evaluate(`document.querySelector('[data-testid="settings-close"]').click()`);
    await expect(page.locator('[data-testid="chat-supervised-title"]')).toContainText('开始新的监督会话');
    await openSettings(page);
    await page.evaluate(`document.querySelector('[data-testid="lang-en"]').click()`);
    await page.evaluate(`document.querySelector('[data-testid="settings-close"]').click()`);
    await expect(page.locator('[data-testid="chat-supervised-title"]')).toContainText('Start a supervised session');
  });

  await test.step('G-02 right panel toggle', async () => {
    await page.click('[data-testid="right-panel-toggle"]');
    await page.click('[data-testid="right-panel-toggle"]');
  });

  await test.step('sandbox path guard', async () => {
    const workspacePath = (await page.evaluate(`
      (async function() {
        const res = await fetch('/api/workspace');
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
