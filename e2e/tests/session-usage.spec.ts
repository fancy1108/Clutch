import { test, expect } from '@playwright/test';
import { connectRunWebSocket } from '../helpers/ws.js';

const sandbox = process.env.CLUTCH_E2E_SANDBOX ?? '';

async function plainChatOverWebSocket(runId: string, text: string): Promise<void> {
  let sent = false;
  await connectRunWebSocket(runId, {
    timeoutMs: 60_000,
    onOpen: (ws) => {
      ws.send(JSON.stringify({ text }));
      sent = true;
    },
    onMessage: (payload) => {
      if (!sent || payload.event !== 'message') return false;
      const message = payload.data?.message as { agent?: string } | undefined;
      return Boolean(message?.agent && message.agent !== 'User');
    },
  });
}

type UsageState = {
  session_tokens?: number;
  token_input?: number;
  token_output?: number;
  usage_estimated?: boolean;
};

async function waitForUsageState(
  request: {
    get: (url: string) => Promise<{ ok: () => boolean; json: () => Promise<{ state: UsageState }> }>;
  },
  runId: string,
  timeoutMs = 20_000,
): Promise<UsageState> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await request.get(`/api/runs/${runId}/state`);
    if (res.ok()) {
      const body = await res.json();
      if (Number(body.state.session_tokens || 0) > 0) return body.state;
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`session_tokens still 0 after ${timeoutMs}ms (run_id=${runId})`);
}

test.describe('session usage (API)', () => {
  test.skip(!sandbox, 'CLUTCH_E2E_SANDBOX required');

  test('plain chat writes provider usage onto GET /state', async ({ request }) => {
    const workspaceRes = await request.post('/api/workspaces', { data: { path: sandbox } });
    expect(workspaceRes.ok()).toBeTruthy();
    const workspace = await workspaceRes.json();
    await request.post(`/api/workspaces/${workspace.id}/activate`);

    const runId = `run_e2e_usage_${Date.now().toString(36)}`;
    const sessionRes = await request.post('/api/sessions', {
      data: { run_id: runId, title: 'e2e usage chat' },
    });
    expect(sessionRes.ok()).toBeTruthy();

    await plainChatOverWebSocket(runId, 'hello usage e2e');

    const state = await waitForUsageState(request, runId);
    expect(Number(state.session_tokens)).toBeGreaterThan(0);
    expect(Number(state.token_input)).toBeGreaterThan(0);
    expect(Number(state.token_output)).toBeGreaterThan(0);
    expect(state.usage_estimated).toBe(false);
  });
});
