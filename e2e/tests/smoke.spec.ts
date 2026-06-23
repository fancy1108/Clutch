import { test, expect } from '@playwright/test';
import { connectRunWebSocket } from '../helpers/ws.js';

test('sidecar health endpoint responds ok', async ({ request }) => {
  const response = await request.get('/health');
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe('ok');
});

test('websocket emits state_patch on connect', async () => {
  const events: string[] = [];
  await connectRunWebSocket('run_e2e_smoke', {
    timeoutMs: 5_000,
    onMessage: (payload) => {
      events.push(payload.event);
      return payload.event === 'state_patch';
    },
  });
  expect(events).toContain('state_patch');
});
