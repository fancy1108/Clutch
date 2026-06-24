import { test, expect } from '@playwright/test';

test.describe('i18n preferences (API)', () => {
  test('language preference round-trips through sidecar', async ({ request }) => {
    const save = await request.post('/api/preferences/language', {
      data: { language: 'zh' },
    });
    expect(save.ok()).toBeTruthy();
    const saved = await save.json();
    expect(saved.active_language).toBe('zh');

    const load = await request.get('/api/preferences/language');
    expect(load.ok()).toBeTruthy();
    const body = await load.json();
    expect(body.active_language).toBe('zh');

    await request.post('/api/preferences/language', { data: { language: 'en' } });
  });
});
