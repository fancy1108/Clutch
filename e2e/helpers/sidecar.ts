export function sidecarBaseUrl(): string {
  const port = process.env.CLUTCH_E2E_SIDECAR_PORT || '8124';
  return `http://127.0.0.1:${port}`;
}

export async function sidecarFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${sidecarBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`;
  return fetch(url, init);
}

export async function waitForSidecarHealth(timeoutMs = 60_000): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await sidecarFetch('/health');
      if (res.ok) return;
    } catch {
      // retry
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Sidecar health timeout (${sidecarBaseUrl()})`);
}

/** Stop any runs still `running` so serial E2E tests do not block each other. */
export async function drainRunningSidecarRuns(): Promise<void> {
  const histRes = await sidecarFetch('/api/runs/history');
  if (!histRes.ok) return;
  const hist = (await histRes.json()) as { runs: Array<{ run_id: string }> };
  for (const { run_id: runId } of hist.runs) {
    const stateRes = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (!stateRes.ok) continue;
    const body = (await stateRes.json()) as { state: { status: string } };
    if (body.state.status === 'running') {
      await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/stop`, { method: 'POST' });
    }
  }
  await new Promise((r) => setTimeout(r, 1500));
}

export type RunUsageState = {
  session_tokens: number;
  token_input: number;
  token_output: number;
  usage_estimated?: boolean;
};

/** Poll GET /api/runs/{id}/state until session_tokens is applied after a chat turn. */
export async function waitForRunUsage(runId: string, timeoutMs = 20_000): Promise<RunUsageState> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await sidecarFetch(`/api/runs/${encodeURIComponent(runId)}/state`);
    if (res.ok) {
      const body = (await res.json()) as { state: RunUsageState };
      if (Number(body.state.session_tokens || 0) > 0) {
        return body.state;
      }
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`session_tokens still 0 after ${timeoutMs}ms (run_id=${runId})`);
}
