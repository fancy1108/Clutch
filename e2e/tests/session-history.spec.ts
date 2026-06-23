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

test.describe('session history (API)', () => {
  test.skip(!sandbox, 'CLUTCH_E2E_SANDBOX required');

  test('plain chat persists messages; GET /state restores conversation', async ({ request }) => {
    const workspaceRes = await request.post('/api/workspaces', { data: { path: sandbox } });
    expect(workspaceRes.ok()).toBeTruthy();
    const workspace = await workspaceRes.json();
    await request.post(`/api/workspaces/${workspace.id}/activate`);

    const runId = `run_e2e_hist_${Date.now().toString(36)}`;
    const sessionRes = await request.post('/api/sessions', {
      data: { run_id: runId, title: 'e2e history chat' },
    });
    expect(sessionRes.ok()).toBeTruthy();

    await plainChatOverWebSocket(runId, '你好 e2e');

    const stateRes = await request.get(`/api/runs/${runId}/state`);
    expect(stateRes.ok()).toBeTruthy();
    const body = (await stateRes.json()) as {
      state: { messages: Array<{ agent: string; text: string }> };
    };
    expect(body.state.messages.length).toBeGreaterThanOrEqual(2);
    expect(body.state.messages.some((m) => m.text.includes('你好 e2e'))).toBeTruthy();
    expect(body.state.messages.some((m) => m.agent !== 'User')).toBeTruthy();

    const historyRes = await request.get('/api/runs/history');
    expect(historyRes.ok()).toBeTruthy();
    const history = (await historyRes.json()) as { runs: Array<{ run_id: string; title?: string }> };
    expect(history.runs.some((r) => r.run_id === runId)).toBeTruthy();
  });
});
