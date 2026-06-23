import { test, expect } from '@playwright/test';

test('sidecar health endpoint responds ok', async ({ request }) => {
  const response = await request.get('/health');
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.status).toBe('ok');
});

test('websocket emits state_patch on connect', async () => {
  const { chromium } = await import('@playwright/test');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const events: string[] = [];
  await page.evaluate(() => {
    (window as unknown as { __events: string[] }).__events = [];
    const ws = new WebSocket('ws://127.0.0.1:8123/ws/runs/e2e_smoke');
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data) as { event: string };
      (window as unknown as { __events: string[] }).__events.push(payload.event);
    };
  });
  await page.waitForTimeout(500);
  const collected = await page.evaluate(() => (window as unknown as { __events: string[] }).__events);
  await browser.close();
  expect(collected).toContain('state_patch');
});
