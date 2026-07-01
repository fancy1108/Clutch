import { setTextareaValue, delay } from './tauri.js';
import { sidecarFetch } from './sidecar.js';

type ConsoleIssue = { type: 'error' | 'pageerror'; text: string };

type TauriPage = {
  click: (selector: string) => Promise<void>;
  waitForSelector: (selector: string, timeout?: number) => Promise<void>;
  locator: (selector: string) => {
    count: () => Promise<number>;
    click: () => Promise<void>;
    isVisible: () => Promise<boolean>;
  };
  evaluate: (script: string) => Promise<unknown>;
  on: (event: string, handler: (payload: unknown) => void) => void;
};

export function attachConsoleGuard(page: TauriPage, issues: ConsoleIssue[]): void {
  if (typeof (page as { on?: unknown }).on !== 'function') {
    return;
  }
  page.on('console', (msg: unknown) => {
    const payload = msg as { type?: () => string; text?: () => string };
    const type = payload.type?.();
    if (type !== 'error') return;
    const text = payload.text?.() ?? '';
    if (/devtools|favicon|Failed to load resource/i.test(text)) return;
    issues.push({ type: 'error', text });
  });
  page.on('pageerror', (err: unknown) => {
    const text = err instanceof Error ? err.message : String(err);
    issues.push({ type: 'pageerror', text });
  });
}

export function assertNoConsoleIssues(issues: ConsoleIssue[]): void {
  if (issues.length === 0) return;
  const detail = issues.map((item) => `${item.type}: ${item.text}`).join('\n');
  throw new Error(`Console issues detected:\n${detail}`);
}

export async function startNewChat(page: TauriPage): Promise<void> {
  await page.click('[data-testid="nav-new-chat"]');
  await page.waitForSelector('[data-testid="chat-input"]', 30_000);
}

export async function sendChatMessage(page: TauriPage, text: string): Promise<void> {
  await setTextareaValue(page, '[data-testid="chat-input"]', text);
  await page.click('[data-testid="chat-send"]');
}

/** Fire first send without awaiting completion so a second message can queue behind a slow turn. */
export async function sendChatMessageBurst(page: TauriPage, texts: string[]): Promise<void> {
  if (texts.length === 0) return;
  for (let i = 0; i < texts.length; i += 1) {
    await setTextareaValue(page, '[data-testid="chat-input"]', texts[i]);
    if (i < texts.length - 1) {
      void page.click('[data-testid="chat-send"]');
      await delay(50);
    } else {
      await page.click('[data-testid="chat-send"]');
    }
  }
}

/** Current session run_id: newest run_* in localStorage (matches React sessionRunId), sidebar as fallback. */
export async function getCurrentSessionRunId(page: TauriPage): Promise<string | null> {
  return (await page.evaluate(`
    (function() {
      let best = null;
      let bestSlug = '';
      for (const key of Object.keys(localStorage)) {
        if (!key.startsWith('clutch_session_agent_')) continue;
        const runId = key.slice('clutch_session_agent_'.length);
        if (!runId.startsWith('run_')) continue;
        const slug = runId.slice(4);
        if (slug >= bestSlug) {
          bestSlug = slug;
          best = runId;
        }
      }
      if (best) return best;
      const sessions = Array.from(document.querySelectorAll('[data-testid^="sidebar-session-"]'));
      const active = sessions.find((el) => (el.className || '').includes('font-bold'));
      if (!active) return null;
      const tid = active.getAttribute('data-testid') || '';
      return tid.replace('sidebar-session-', '') || null;
    })()
  `)) as string | null;
}

export async function waitForCurrentSessionRunId(page: TauriPage, timeoutMs: number): Promise<string> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const runId = await getCurrentSessionRunId(page);
    if (runId) return runId;
    await delay(200);
  }
  throw new Error('Could not resolve active session run_id (sidebar or localStorage)');
}

function isAssistantMessage(m: { agent: string }): boolean {
  return Boolean(m.agent && m.agent !== 'User' && m.agent !== 'Supervisor');
}

export async function waitForRunIdle(runId: string, timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const stateRes = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (stateRes.ok) {
      const body = (await stateRes.json()) as { state: { status: string } };
      const status = body.state.status;
      if (status === 'idle' || status === 'passed' || status === 'failed') return;
    }
    await delay(500);
  }
  throw new Error(`Run idle timeout after ${timeoutMs}ms (run_id=${runId})`);
}

export async function waitForRunStatus(
  runId: string,
  status: string,
  timeoutMs: number,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const stateRes = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (stateRes.ok) {
      const body = (await stateRes.json()) as { state: { status: string } };
      if (body.state.status === status) return;
    }
    await delay(200);
  }
  throw new Error(`Run status "${status}" timeout after ${timeoutMs}ms (run_id=${runId})`);
}

/** Both user turns visible while run still busy (queued second message before first reply). */
export async function waitForQueuedUserMessages(
  runId: string,
  userTexts: string[],
  timeoutMs: number,
): Promise<void> {
  const needles = userTexts.map((text) => text.trim());
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const stateRes = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (stateRes.ok) {
      const body = (await stateRes.json()) as {
        state: {
          status: string;
          messages: Array<{ agent: string; text: string }>;
        };
      };
      const messages = body.state.messages ?? [];
      const userMessages = messages.filter((m) => m.agent === 'User');
      const hasAll = needles.every((needle) =>
        userMessages.some((m) => (m.text ?? '').trim().includes(needle)),
      );
      const assistants = messages.filter(isAssistantMessage);
      if (hasAll && body.state.status === 'running' && assistants.length < needles.length) {
        return;
      }
    }
    await delay(300);
  }
  throw new Error(
    `Queued user messages not observed while running after ${timeoutMs}ms (run_id=${runId})`,
  );
}

export async function fetchActiveModelId(): Promise<string> {
  const res = await sidecarFetch('/api/models/config');
  if (!res.ok) throw new Error(`models/config failed (${res.status})`);
  const body = (await res.json()) as { active_model_id?: string };
  return body.active_model_id ?? '';
}

export async function waitForUserMessage(
  runId: string,
  userText: string,
  timeoutMs: number,
): Promise<void> {
  const needle = userText.trim();
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const stateRes = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (stateRes.ok) {
      const body = (await stateRes.json()) as {
        state: { messages: Array<{ agent: string; text: string }> };
      };
      const hasUser = (body.state.messages ?? []).some(
        (m) => m.agent === 'User' && (m.text ?? '').trim().includes(needle),
      );
      if (hasUser) return;
    }
    await delay(500);
  }
  throw new Error(`User message not found on run_id=${runId}: ${needle}`);
}

export async function waitForWorkflowRunning(
  runId: string,
  workflowId: string,
  timeoutMs: number,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const stateRes = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (stateRes.ok) {
      const body = (await stateRes.json()) as {
        state: { workflow_id?: string; status: string };
      };
      if (body.state.workflow_id === workflowId && body.state.status === 'running') return;
    }
    await delay(500);
  }
  throw new Error(`Workflow ${workflowId} did not start on run_id=${runId}`);
}

async function readAssistantTextsFromDom(page: TauriPage): Promise<string[]> {
  return (await page.evaluate(`
    (function() {
      const bubbles = Array.from(document.querySelectorAll('.justify-start .rounded-tl-none'));
      return bubbles
        .map((el) => (el.textContent || '').replace(/\\s+/g, ' ').trim())
        .filter(Boolean);
    })()
  `)) as string[];
}

function normalizeReplyText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function findMatchingAssistantReply(
  assistants: Array<{ agent: string; text: string }>,
  options: {
    minCount: number;
    afterText?: string;
    matcher: RegExp | null;
    requireIdle: boolean;
    idle: boolean;
  },
): string | null {
  const { minCount, afterText, matcher, requireIdle, idle } = options;
  if (requireIdle && !idle) return null;
  if (assistants.length <= minCount) return null;
  const afterNorm = afterText ? normalizeReplyText(afterText) : '';
  for (let i = assistants.length - 1; i >= 0; i -= 1) {
    const text = normalizeReplyText(assistants[i]?.text ?? '');
    if (!text) continue;
    if (afterNorm && text === afterNorm) continue;
    if (matcher && !matcher.test(text)) continue;
    return text;
  }
  return null;
}

export async function waitForAssistantReply(
  page: TauriPage,
  timeoutMs: number,
  hint?: string | RegExp,
  options?: { runId: string; afterAssistantCount?: number; afterText?: string },
): Promise<string> {
  if (!options?.runId) {
    throw new Error('waitForAssistantReply requires options.runId (bind to sidebar session)');
  }
  const runId = options.runId;
  const matcher = hint instanceof RegExp ? hint : hint ? new RegExp(hint, 'i') : null;
  const deadline = Date.now() + timeoutMs;
  const minCount = options.afterAssistantCount ?? 0;
  const afterNorm = options.afterText ? normalizeReplyText(options.afterText) : '';

  while (Date.now() < deadline) {
    const stateRes = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (stateRes.ok) {
      const body = (await stateRes.json()) as {
        state: {
          status: string;
          messages: Array<{ agent: string; text: string }>;
        };
      };
      const status = body.state.status;
      const idle = status === 'idle' || status === 'passed' || status === 'failed';
      const assistants = (body.state.messages ?? []).filter(isAssistantMessage);
      const fromState =
        findMatchingAssistantReply(assistants, {
          minCount,
          afterText: options.afterText,
          matcher,
          requireIdle: true,
          idle,
        }) ??
        (options.afterText
          ? findMatchingAssistantReply(assistants, {
              minCount: Math.max(minCount, 1),
              afterText: options.afterText,
              matcher,
              requireIdle: false,
              idle,
            })
          : null);
      if (fromState) return fromState;
    }

    const domTexts = await readAssistantTextsFromDom(page);
    for (let i = domTexts.length - 1; i >= 0; i -= 1) {
      const text = normalizeReplyText(domTexts[i] ?? '');
      if (!text) continue;
      if (afterNorm && text === afterNorm) continue;
      if (minCount > 0 && i < minCount) continue;
      if (matcher && !matcher.test(text)) continue;
      if (options.afterText && domTexts.length < 2) continue;
      return text;
    }

    await delay(1000);
  }
  throw new Error(`Assistant reply timeout after ${timeoutMs}ms (run_id=${runId})`);
}

export async function selectFooterAgent(page: TauriPage, agentId: string): Promise<void> {
  await page.click('[data-testid="footer-agent-trigger"]');
  await page.waitForSelector('[data-testid="footer-agent-menu"]', 10_000);
  await page.waitForSelector(`[data-testid="footer-agent-item-${agentId}"]`, 10_000);
  await page.click(`[data-testid="footer-agent-item-${agentId}"]`);
  const deadline = Date.now() + 10_000;
  while (Date.now() < deadline) {
    const selected = (await page.evaluate(`
      (function() {
        let best = null;
        let bestSlug = '';
        for (const key of Object.keys(localStorage)) {
          if (!key.startsWith('clutch_session_agent_')) continue;
          const runId = key.slice('clutch_session_agent_'.length);
          if (!runId.startsWith('run_')) continue;
          const slug = runId.slice(4);
          if (slug >= bestSlug) { bestSlug = slug; best = runId; }
        }
        if (best) {
          const stored = localStorage.getItem('clutch_session_agent_' + best);
          if (stored) return stored;
        }
        return localStorage.getItem('clutch_active_agent_id') || '';
      })()
    `)) as string;
    if (selected === agentId) return;
    await delay(200);
  }
  throw new Error(`Footer agent not selected: ${agentId}`);
}

export async function selectFooterModel(page: TauriPage, modelId: string): Promise<void> {
  await page.click('[data-testid="footer-model-trigger"]');
  await page.waitForSelector('[data-testid="footer-model-menu"]', 10_000);
  await page.click(`[data-testid="footer-model-item-${modelId}"]`);
}

/** Cross-agent / text chat: bind a text LLM and verify sidecar active_model_id (not image model). */
export async function selectFooterTextModel(page: TauriPage, textModelId: string): Promise<void> {
  await selectFooterModel(page, textModelId);
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    const res = await sidecarFetch('/api/models/config');
    if (res.ok) {
      const body = (await res.json()) as { active_model_id?: string };
      if (body.active_model_id === textModelId) return;
    }
    await delay(300);
  }
  throw new Error(`Footer text model not active: ${textModelId}`);
}

export async function clearWorkflowSelection(page: TauriPage): Promise<void> {
  const trigger = page.locator('[data-testid="footer-workflow-trigger"]');
  if ((await trigger.count()) === 0) return;
  await trigger.click();
  const menu = page.locator('[data-testid="footer-workflow-menu"]');
  if ((await menu.count()) === 0) return;
  const selected = await page.evaluate(`
    (function() {
      const items = Array.from(document.querySelectorAll('[data-testid^="footer-workflow-item-"]'));
      const active = items.find((el) => el.querySelector('.text-primary.font-bold'));
      return active ? active.getAttribute('data-testid') : null;
    })()
  `);
  if (selected) {
    await page.click(`[data-testid="${selected}"]`);
  }
}

export async function waitForWorkflowComplete(
  runId: string,
  workflowId: string,
  timeoutMs: number,
): Promise<{ status: string; messageCount: number; hasImage: boolean }> {
  const start = Date.now();
  let sawRunning = false;
  while (Date.now() - start < timeoutMs) {
    const res = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (!res.ok) {
      await delay(1000);
      continue;
    }
    const body = (await res.json()) as {
      state: {
        workflow_id?: string;
        status: string;
        messages: Array<{ agent: string; text: string; imageUrl?: string }>;
      };
    };
    const state = body.state;
    if (state.workflow_id !== workflowId) {
      await delay(1000);
      continue;
    }
    if (state.status === 'running') {
      sawRunning = true;
    }
    const messages = state.messages ?? [];
    const hasImage = messages.some((m) => Boolean(m.imageUrl) || /<img|image/i.test(m.text || ''));
    const terminal = state.status === 'passed' || state.status === 'idle' || state.status === 'failed';
    if (terminal) {
      if (state.status === 'failed') {
        throw new Error(`Workflow failed: ${JSON.stringify(messages.slice(-2))}`);
      }
      const assistantCount = messages.filter((m) => m.agent && m.agent !== 'User').length;
      if (sawRunning && assistantCount >= 5 && messages.length >= 6) {
        return { status: state.status, messageCount: messages.length, hasImage };
      }
    }
    await delay(2000);
  }
  throw new Error(`Workflow completion timeout after ${timeoutMs}ms (run_id=${runId})`);
}
