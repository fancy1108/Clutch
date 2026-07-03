import { test, expect } from '@playwright/test';
import { connectRunWebSocket } from '../helpers/ws.js';

const sandbox = process.env.CLUTCH_E2E_SANDBOX ?? '';

async function activateSandboxWorkspace(request: {
  post: (url: string, options?: { data?: unknown }) => Promise<{ ok: () => boolean; json: () => Promise<unknown> }>;
}): Promise<void> {
  const workspaceRes = await request.post('/api/workspaces', { data: { path: sandbox } });
  expect(workspaceRes.ok()).toBeTruthy();
  const workspace = (await workspaceRes.json()) as { id: string };
  await request.post(`/api/workspaces/${workspace.id}/activate`);
}

test.describe('terminal orchestra dispatch (API)', () => {
  test.skip(!sandbox, 'CLUTCH_E2E_SANDBOX required');

  test('dispatch preview rejects input without @agent', async ({ request }) => {
    await activateSandboxWorkspace(request);
    const runId = `run_d34_preview_fail_${Date.now().toString(36)}`;

    await connectRunWebSocket(runId, {
      timeoutMs: 15_000,
      onOpen: (ws) => {
        ws.send(JSON.stringify({ action: 'dispatch_preview', text: 'hello without agent' }));
      },
      onMessage: (payload) => {
        if (payload.event !== 'dispatch_preview') return false;
        expect(payload.data?.ok).toBe(false);
        return true;
      },
    });
  });

  test('dispatch preview + confirm creates lanes, log, and handoff file', async ({ request }) => {
    await activateSandboxWorkspace(request);
    const runId = `run_d34_confirm_${Date.now().toString(36)}`;
    const prompt = '@OpenCode 实现 API';
    let wsRef: WebSocket | null = null;

    await connectRunWebSocket(runId, {
      timeoutMs: 20_000,
      onOpen: (ws) => {
        wsRef = ws;
        ws.send(JSON.stringify({ action: 'dispatch_preview', text: prompt }));
      },
      onMessage: (payload) => {
        if (payload.event === 'dispatch_preview') {
          expect(payload.data?.ok).toBe(true);
          const preview = payload.data?.preview as { target?: string };
          expect(preview?.target).toBe('OpenCode');
          wsRef?.send(JSON.stringify({ action: 'dispatch_confirm', text: prompt }));
          return false;
        }
        if (payload.event === 'state_patch') {
          const patch = payload.data?.patch as { dispatch_log?: unknown[] } | undefined;
          if (patch?.dispatch_log && patch.dispatch_log.length > 0) return true;
        }
        return false;
      },
    });

    const stateRes = await request.get(`/api/runs/${encodeURIComponent(runId)}/state`);
    expect(stateRes.ok()).toBeTruthy();
    const body = (await stateRes.json()) as {
      state: {
        dispatch_log: Array<{ target: string; handoff_path: string }>;
        dispatch_edges: Array<{ target: string }>;
        pty_lanes: Array<{ agent_type: string }>;
      };
    };
    expect(body.state.dispatch_log.length).toBeGreaterThanOrEqual(1);
    expect(body.state.dispatch_log[0].target).toBe('OpenCode');
    expect(body.state.dispatch_edges.length).toBeGreaterThanOrEqual(1);
    expect(body.state.pty_lanes.some((lane) => lane.agent_type === 'opencode-cli')).toBeTruthy();

    const handoffPath = body.state.dispatch_log[0].handoff_path;
    const fileRes = await request.get(
      `/api/workspace/file?path=${encodeURIComponent(handoffPath)}`,
    );
    expect(fileRes.ok()).toBeTruthy();
    const fileBody = (await fileRes.json()) as { content: string };
    expect(fileBody.content).toContain('OpenCode');
  });

  test('lane_complete appends pending handoff draft', async ({ request }) => {
    await activateSandboxWorkspace(request);
    const runId = `run_d34_complete_${Date.now().toString(36)}`;
    const prompt = '@OpenCode 实现 CRUD';
    let wsRef: WebSocket | null = null;
    let laneId = '';

    await connectRunWebSocket(runId, {
      timeoutMs: 20_000,
      onOpen: (ws) => {
        wsRef = ws;
        ws.send(JSON.stringify({ action: 'dispatch_confirm', text: prompt }));
      },
      onMessage: (payload) => {
        if (payload.event === 'state_patch') {
          const patch = payload.data?.patch as {
            focused_lane_id?: string;
            pending_handoff_drafts?: unknown[];
            dispatch_log?: unknown[];
          } | undefined;
          if (
            !laneId
            && patch?.focused_lane_id
            && patch.dispatch_log
            && patch.dispatch_log.length > 0
          ) {
            laneId = patch.focused_lane_id;
            wsRef?.send(JSON.stringify({ action: 'lane_complete', lane_id: laneId }));
            return false;
          }
          if (patch?.pending_handoff_drafts && patch.pending_handoff_drafts.length > 0) {
            return true;
          }
        }
        return false;
      },
    });

    const stateRes = await request.get(`/api/runs/${encodeURIComponent(runId)}/state`);
    const body = (await stateRes.json()) as {
      state: { pending_handoff_drafts: Array<{ text: string }> };
    };
    expect(body.state.pending_handoff_drafts.length).toBeGreaterThanOrEqual(1);
    expect(body.state.pending_handoff_drafts[0].text).toContain('@');
  });
});
