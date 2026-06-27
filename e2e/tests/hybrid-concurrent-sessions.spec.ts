import { test, expect } from '@playwright/test';
import { hybridPlainChatUntilIdle } from '../helpers/hybrid.js';

const sandbox = process.env.CLUTCH_E2E_SANDBOX ?? '';
const hybridMode = process.env.CLUTCH_RUNTIME_MODE === 'hybrid';
const fakeHybrid = process.env.CLUTCH_E2E_FAKE_HYBRID === '1';
const agentId = 'agent-e2e-hybrid';

test.describe('hybrid concurrent sessions (API)', () => {
  test.skip(!sandbox, 'CLUTCH_E2E_SANDBOX required');
  test.skip(!hybridMode, 'CLUTCH_RUNTIME_MODE=hybrid required');
  test.skip(!fakeHybrid, 'CLUTCH_E2E_FAKE_HYBRID=1 required (fake Claude turn; real PTY spawn)');

  test('two run_ids complete when messages are sent concurrently', async ({ request }) => {
    const workspaceRes = await request.post('/api/workspaces', { data: { path: sandbox } });
    expect(workspaceRes.ok()).toBeTruthy();
    const workspace = await workspaceRes.json();
    await request.post(`/api/workspaces/${workspace.id}/activate`);

    const stamp = Date.now().toString(36);
    const runA = `run_e2e_hybrid_a_${stamp}`;
    const runB = `run_e2e_hybrid_b_${stamp}`;

    for (const [runId, title] of [
      [runA, '这是对话1'],
      [runB, '这是对话2'],
    ] as const) {
      const sessionRes = await request.post('/api/sessions', {
        data: { run_id: runId, title },
      });
      expect(sessionRes.ok()).toBeTruthy();
    }

    const [resultA, resultB] = await Promise.all([
      hybridPlainChatUntilIdle(runA, '这是对话1', agentId),
      hybridPlainChatUntilIdle(runB, '这是对话2', agentId),
    ]);

    expect(resultA.status).toBe('idle');
    expect(resultB.status).toBe('idle');

    const stateA = await request.get(`/api/runs/${runA}/state`);
    const stateB = await request.get(`/api/runs/${runB}/state`);
    expect(stateA.ok()).toBeTruthy();
    expect(stateB.ok()).toBeTruthy();

    const bodyA = (await stateA.json()) as {
      state: {
        status: string;
        shell_session_status?: string;
        messages: Array<{ agent: string; text: string }>;
        terminal_logs?: string[];
      };
    };
    const bodyB = (await stateB.json()) as {
      state: {
        status: string;
        shell_session_status?: string;
        messages: Array<{ agent: string; text: string }>;
        terminal_logs?: string[];
      };
    };

    const replyA =
      bodyA.state.messages.find((message) => message.agent === 'Claude E2E Hybrid')?.text ??
      resultA.replyText;
    const replyB =
      bodyB.state.messages.find((message) => message.agent === 'Claude E2E Hybrid')?.text ??
      resultB.replyText;
    const logsA = [...resultA.logs, ...(bodyA.state.terminal_logs ?? [])].join('\n');
    const logsB = [...resultB.logs, ...(bodyB.state.terminal_logs ?? [])].join('\n');

    expect(replyA).toContain('这是对话1');
    expect(replyB).toContain('这是对话2');
    expect(logsA).toMatch(/\[HYBRID\] acquiring shell/);
    expect(logsB).toMatch(/\[HYBRID\] acquiring shell/);
    expect(logsA).toMatch(/\[HYBRID\] shell ready/);
    expect(logsB).toMatch(/\[HYBRID\] shell ready/);
    expect(logsA).not.toMatch(/pool_full|rejected_pool_full/);
    expect(logsB).not.toMatch(/pool_full|rejected_pool_full/);

    expect(bodyA.state.status).toBe('idle');
    expect(bodyB.state.status).toBe('idle');
    expect(bodyA.state.shell_session_status).not.toBe('rejected_pool_full');
    expect(bodyB.state.shell_session_status).not.toBe('rejected_pool_full');
    expect(
      bodyA.state.messages.some((message) => message.agent === 'Claude E2E Hybrid'),
    ).toBeTruthy();
    expect(
      bodyB.state.messages.some((message) => message.agent === 'Claude E2E Hybrid'),
    ).toBeTruthy();
  });
});
