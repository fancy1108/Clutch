import { test, expect } from '@playwright/test';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

test('mvp closed loop: template → check fail → human approve → pass', async ({ request }) => {
  const workspace = mkdtempSync(join(tmpdir(), 'clutch-e2e-'));

  const authorize = await request.post('/api/workspace', { data: { path: workspace } });
  expect(authorize.ok()).toBeTruthy();

  const start = await request.post('/api/runs/start', {
    data: { workflow_id: 'video-production', instruction: 'e2e mvp' },
  });
  expect(start.ok()).toBeTruthy();
  const started = await start.json();
  expect(started.status).toBe('awaiting_human');

  const approve = await request.post(`/api/runs/${started.run_id}/human-decision`, {
    data: { decision: 'approve' },
  });
  expect(approve.ok()).toBeTruthy();
  const finalState = await approve.json();
  expect(finalState.status).toBe('passed');
});
