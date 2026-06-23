/** Start MVP workflow via Sidecar HTTP (sandbox lacks verify.md → awaiting_human). */
export async function startVideoProductionRun(instruction: string): Promise<string> {
  const authorize = await fetch('http://127.0.0.1:8123/api/workspace', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: process.env.CLUTCH_E2E_SANDBOX }),
  });
  if (!authorize.ok) {
    throw new Error(`workspace authorize failed: ${authorize.status}`);
  }

  const start = await fetch('http://127.0.0.1:8123/api/runs/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ workflow_id: 'video-production', instruction }),
  });
  if (!start.ok) {
    throw new Error(`workflow start failed: ${start.status}`);
  }
  const body = (await start.json()) as { run_id: string; status: string };
  if (body.status !== 'awaiting_human') {
    throw new Error(`expected awaiting_human, got ${body.status}`);
  }
  return body.run_id;
}
