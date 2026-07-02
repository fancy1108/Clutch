import { setTextareaValue } from '../../helpers/tauri.js';
import {
  attachConsoleGuard,
  assertNoConsoleIssues,
  clearWorkflowSelection,
  selectFooterAgent,
  startNewChat,
  waitForCurrentSessionRunId,
} from '../../helpers/chat-ui.js';
import { test, expect } from '../../fixtures/desktop.js';
import { authorizeSandboxWorkspace } from '../../helpers/tauri.js';

const consoleIssues: Array<{ type: 'error' | 'pageerror'; text: string }> = [];

test.afterEach(() => {
  assertNoConsoleIssues(consoleIssues);
  consoleIssues.length = 0;
});

async function switchToTerminalMode(page: Parameters<typeof attachConsoleGuard>[0]): Promise<void> {
  await page.waitForSelector('[data-testid="workspace-view-terminal"]', 15_000);
  await page.click('[data-testid="workspace-view-terminal"]');
  await page.waitForSelector('[data-testid="orchestrator-bar"]', 15_000);
}

test('D34 terminal orchestra UI smoke', async ({ tauriPage: page }) => {
  test.setTimeout(120_000);
  attachConsoleGuard(page, consoleIssues);

  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, 'agent-e2e-hybrid');

  await switchToTerminalMode(page);
  await expect(page.locator('[data-testid="chat-input"]')).toHaveCount(0);
  await expect(page.locator('[data-testid="terminal-orchestra-workspace"]')).toBeVisible();
  await expect(page.locator('[data-testid="orchestrator-input"]')).toBeVisible();

  const prompt = '@OpenCode 实现 API';
  await setTextareaValue(page, '[data-testid="orchestrator-input"]', prompt);
  await page.click('[data-testid="orchestrator-send-btn"]');
  await page.waitForSelector('[data-testid="dispatch-confirm-card"]', 15_000);
  await page.click('[data-testid="confirm-dispatch-btn"]');

  await page.click('[data-testid="right-tab-overview"]');
  await page.waitForSelector('[data-testid="overview-dispatch-log"] li', 15_000);

  await page.click('[data-testid="workspace-view-chat"]');
  await page.waitForSelector('[data-testid="chat-input"]', 15_000);
  await expect(page.locator('[data-testid="orchestrator-bar"]')).toHaveCount(0);
});

test('D34 orchestrator shows error for invalid dispatch', async ({ tauriPage: page }) => {
  test.setTimeout(90_000);
  attachConsoleGuard(page, consoleIssues);

  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, 'agent-e2e-hybrid');
  await switchToTerminalMode(page);

  await setTextareaValue(page, '[data-testid="orchestrator-input"]', 'no agent mention');
  await page.click('[data-testid="orchestrator-send-btn"]');
  await page.waitForSelector('[data-testid="orchestrator-dock-error"]', 15_000);
});
