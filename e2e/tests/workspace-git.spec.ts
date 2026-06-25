import { test, expect } from '@playwright/test';

const sandbox = process.env.CLUTCH_E2E_SANDBOX ?? '';

test.describe('workspace git (API)', () => {
  test.skip(!sandbox, 'CLUTCH_E2E_SANDBOX required');

  test('GET /api/workspace/git returns branch for sandbox repo', async ({ request }) => {
    const workspaceRes = await request.post('/api/workspaces', { data: { path: sandbox } });
    expect(workspaceRes.ok()).toBeTruthy();
    const workspace = await workspaceRes.json();
    await request.post(`/api/workspaces/${workspace.id}/activate`);

    const gitRes = await request.get('/api/workspace/git');
    expect(gitRes.ok()).toBeTruthy();
    const body = (await gitRes.json()) as {
      is_git_repo: boolean;
      branch: string | null;
      branches: string[];
    };
    expect(body.is_git_repo).toBe(true);
    expect(body.branch).toBeTruthy();
    expect(body.branches).toContain(body.branch);
  });
});
