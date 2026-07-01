import { test, expect } from '../../fixtures/desktop.js';
import { authorizeSandboxWorkspace } from '../../helpers/tauri.js';
import {
  loadAcceptanceConfig,
  loadAcceptanceManifest,
  cliAgentId,
  ollamaModelId,
} from '../../helpers/acceptance-config.js';
import {
  attachConsoleGuard,
  assertNoConsoleIssues,
  clearWorkflowSelection,
  selectFooterAgent,
  selectFooterModel,
  selectFooterTextModel,
  sendChatMessage,
  sendChatMessageBurst,
  startNewChat,
  waitForAssistantReply,
  waitForCurrentSessionRunId,
  waitForHybridShellReady,
  waitForQueuedPoolStatus,
  waitForQueuedUserMessages,
  waitForRunIdle,
  waitForRunStatus,
  waitForUserMessage,
  waitForWorkflowComplete,
  waitForWorkflowRunning,
} from '../../helpers/chat-ui.js';
import { drainRunningSidecarRuns, sidecarFetch, waitForSidecarHealth } from '../../helpers/sidecar.js';
import { delay } from '../../helpers/tauri.js';

const config = loadAcceptanceConfig();
const manifest = loadAcceptanceManifest();
const t = config.test_timeouts_ms;
const consoleIssues: Array<{ type: 'error' | 'pageerror'; text: string }> = [];

test.beforeAll(async () => {
  await waitForSidecarHealth(t.sidecar_health);
});

test.afterEach(() => {
  assertNoConsoleIssues(consoleIssues);
  consoleIssues.length = 0;
});

async function prepareChatTest(page: Parameters<typeof attachConsoleGuard>[0]): Promise<void> {
  await drainRunningSidecarRuns();
  await waitForSidecarHealth(30_000);
  attachConsoleGuard(page, consoleIssues);
}

test('U12 settings tabs open without errors', async ({ tauriPage: page }) => {
  test.setTimeout(t.ui);
  attachConsoleGuard(page, consoleIssues);
  await page.waitForSelector('[data-testid="nav-new-chat"]', 10_000);
  await page.click('[data-testid="nav-settings"]');
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
  }
  await page.click('[data-testid="settings-close"]');
});

/** API + cross-agent + workflow before CLI matrix — avoids hybrid/Ollama pool exhaustion. */
test('B1 text API model (real)', async ({ tauriPage: page }) => {
  test.setTimeout(t.api_turn);
  await prepareChatTest(page);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  const runId = await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, 'clutch-agent');
  await selectFooterModel(page, config.api_models.text_model_id);
  await sendChatMessage(page, '请只回复：TEXT-OK');
  const reply = await waitForAssistantReply(page, config.api_timeout_ms, /TEXT-OK|OK/i, { runId });
  expect(reply.length).toBeGreaterThan(0);
});

/** Same session: second send while first turn is running must queue, not drop or reject. */
test('Q1 same-session message queue (real)', async ({ tauriPage: page }) => {
  test.skip(manifest.ollama_tags.length === 0, 'No local Ollama models');
  test.setTimeout(t.ollama_multi);
  await prepareChatTest(page);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  const runId = await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, 'clutch-agent');
  const tag = manifest.ollama_tags[0];
  await selectFooterModel(page, ollamaModelId(tag));
  await sendChatMessageBurst(page, ['请只回复：QUEUE-A', '请只回复：QUEUE-B']);
  await waitForQueuedUserMessages(runId, ['QUEUE-A', 'QUEUE-B'], config.ollama_timeout_ms);
  await waitForUserMessage(runId, 'QUEUE-A', config.ollama_timeout_ms);
  await waitForUserMessage(runId, 'QUEUE-B', config.ollama_timeout_ms);
  const firstReply = await waitForAssistantReply(page, config.ollama_timeout_ms, /QUEUE-A/i, { runId });
  const secondReply = await waitForAssistantReply(page, config.ollama_timeout_ms, /QUEUE-B/i, {
    runId,
    afterText: firstReply,
  });
  expect(firstReply).toMatch(/QUEUE-A/i);
  expect(secondReply).toMatch(/QUEUE-B/i);
  await waitForRunIdle(runId, 15_000);
});

/** Cross-session: when shell pool is full, the next session queues then runs after a slot frees. */
test('P1 cross-session pool queue (real)', async ({ tauriPage: page }) => {
  test.skip(manifest.cli_tools.length === 0, 'No CLI agents available');
  test.setTimeout(t.cross_agent);
  await prepareChatTest(page);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  const runIdA = await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  const claudeTool =
    manifest.cli_tools.find((toolId) => toolId === 'claude-cli') ?? manifest.cli_tools[0];
  await selectFooterAgent(page, cliAgentId(claudeTool));
  await sendChatMessage(page, '请只回复：POOL-HOLD');
  await waitForHybridShellReady(runIdA, 30_000);
  await startNewChat(page);
  const runIdB = await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, cliAgentId(claudeTool));
  await sendChatMessage(page, '请只回复：POOL-WAIT');
  await waitForQueuedPoolStatus(runIdB, config.cross_agent_cli_timeout_ms);
  await waitForUserMessage(runIdB, 'POOL-WAIT', config.cross_agent_cli_timeout_ms);
  await waitForAssistantReply(page, config.cross_agent_cli_timeout_ms, /POOL-HOLD/i, { runId: runIdA });
  const replyB = await waitForAssistantReply(
    page,
    config.cross_agent_cli_timeout_ms,
    /POOL-WAIT/i,
    { runId: runIdB },
  );
  expect(replyB).toMatch(/POOL-WAIT/i);
  await waitForRunIdle(runIdB, 15_000);
});

test('B2 Ollama multi-turn (real)', async ({ tauriPage: page }) => {
  test.skip(manifest.ollama_tags.length === 0, 'No local Ollama models');
  test.setTimeout(t.ollama_multi);
  await prepareChatTest(page);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  const runId = await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, 'clutch-agent');
  const tag = manifest.ollama_tags[0];
  await selectFooterModel(page, ollamaModelId(tag));
  await sendChatMessage(page, '记住暗号 BETA-3，回复 OK');
  await waitForAssistantReply(page, config.ollama_timeout_ms, /OK|BETA/i, { runId });
  await sendChatMessage(page, '我刚才让你记住的暗号是什么？');
  const reply = await waitForAssistantReply(page, config.ollama_timeout_ms, /BETA|3/i, { runId });
  expect(reply).toMatch(/BETA|3/i);
});

test('X1 cross-agent context (real)', async ({ tauriPage: page }) => {
  test.skip(manifest.cli_tools.length === 0, 'No CLI agents available');
  test.setTimeout(t.cross_agent);
  await prepareChatTest(page);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  const runId = await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, 'clutch-agent');
  await selectFooterTextModel(page, config.api_models.text_model_id);
  await sendChatMessage(page, '你好');
  await waitForUserMessage(runId, '你好', config.api_timeout_ms);
  const firstReply = await waitForAssistantReply(page, config.api_timeout_ms, undefined, { runId });
  await waitForRunIdle(runId, 15_000);
  const claudeTool =
    manifest.cli_tools.find((toolId) => toolId === 'claude-cli') ?? manifest.cli_tools[0];
  await selectFooterAgent(page, cliAgentId(claudeTool));
  await sendChatMessage(page, '刚刚我说的什么');
  const reply = await waitForAssistantReply(
    page,
    config.cross_agent_cli_timeout_ms,
    /你好|hello|打招呼|刚才|说了什么|问候/i,
    { runId, afterText: firstReply },
  );
  expect(reply).toMatch(/你好|hello|打招呼|刚才|说了什么|问候/i);
});

test('I1 image API model (real)', async ({ tauriPage: page }) => {
  test.setTimeout(t.image);
  await prepareChatTest(page);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  const runId = await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, 'clutch-agent');
  await selectFooterModel(page, config.api_models.image_model_id);
  await sendChatMessage(page, '画一只简笔画风格的猫');
  await waitForAssistantReply(page, config.api_timeout_ms * 2, undefined, { runId });
  const hasImage = (await page.evaluate(`
    (function() {
      const imgs = document.querySelectorAll('img');
      if (imgs.length > 0) return true;
      const text = document.body.innerText.toLowerCase();
      return text.includes('image') || text.includes('png') || text.includes('jpg');
    })()
  `)) as boolean;
  expect(hasImage).toBeTruthy();
});

/** New Chat after image model must reset footer to default text model (option B). */
test('N1 new chat resets text model after image (real)', async ({ tauriPage: page }) => {
  test.setTimeout(t.api_turn);
  await prepareChatTest(page);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  await waitForCurrentSessionRunId(page, 15_000);
  await clearWorkflowSelection(page);
  await selectFooterAgent(page, 'clutch-agent');
  await selectFooterModel(page, config.api_models.image_model_id);
  const deadline = Date.now() + 15_000;
  let imageActive = '';
  while (Date.now() < deadline) {
    const res = await sidecarFetch('/api/models/config');
    if (res.ok) {
      const body = (await res.json()) as { active_model_id?: string };
      imageActive = body.active_model_id ?? '';
      if (imageActive === config.api_models.image_model_id) break;
    }
    await delay(300);
  }
  expect(imageActive).toBe(config.api_models.image_model_id);
  await startNewChat(page);
  await waitForCurrentSessionRunId(page, 15_000);
  const resetDeadline = Date.now() + 15_000;
  let textActive = '';
  while (Date.now() < resetDeadline) {
    const res = await sidecarFetch('/api/models/config');
    if (res.ok) {
      const body = (await res.json()) as { active_model_id?: string };
      textActive = body.active_model_id ?? '';
      if (textActive === config.api_models.text_model_id) break;
    }
    await delay(300);
  }
  expect(textActive).toBe(config.api_models.text_model_id);
});

test('F1 workflow demo end-to-end (real)', async ({ tauriPage: page }) => {
  test.setTimeout(t.workflow);
  await prepareChatTest(page);
  await authorizeSandboxWorkspace(page);
  await startNewChat(page);
  const runId = await waitForCurrentSessionRunId(page, 15_000);
  await page.click('[data-testid="footer-workflow-trigger"]');
  await page.waitForSelector('[data-testid="footer-workflow-menu"]', 10_000);
  await page.click(`[data-testid="footer-workflow-item-${config.workflow.id}"]`);
  await sendChatMessage(page, config.workflow.start_instruction);
  await waitForWorkflowRunning(runId, config.workflow.id, 15_000);

  const workflowWaitMs = config.workflow.timeout_minutes * 60_000;
  const result = await waitForWorkflowComplete(runId, config.workflow.id, workflowWaitMs);
  expect(result.status === 'passed' || result.status === 'idle').toBeTruthy();
  expect(result.messageCount).toBeGreaterThanOrEqual(6);
});

/** CLI matrix last — each test holds a hybrid shell; run after API/cross-agent/workflow. */
test.describe('CLI matrix (real)', () => {
  for (const toolId of manifest.cli_tools) {
    test(`CLI ${toolId} single-turn`, async ({ tauriPage: page }) => {
      test.setTimeout(t.cli_turn);
      await prepareChatTest(page);
      await page.waitForSelector('[data-testid="nav-new-chat"]', 10_000);
      await authorizeSandboxWorkspace(page);
      await startNewChat(page);
      const runId = await waitForCurrentSessionRunId(page, 15_000);
      await clearWorkflowSelection(page);
      await selectFooterAgent(page, cliAgentId(toolId));
      await sendChatMessage(page, '请只回复一个词：CLI-OK');
      const reply = await waitForAssistantReply(page, config.cli_timeout_ms, /CLI-OK|OK|PONG/i, {
        runId,
      });
      expect(reply.trim().length).toBeGreaterThan(0);
    });
  }
});
