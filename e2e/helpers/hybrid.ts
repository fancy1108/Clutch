const WS_BASE = 'ws://127.0.0.1:8123/ws/runs';

export type HybridChatResult = {
  logs: string[];
  replyText: string;
  status: string;
};

/** Plain-chat over WS until hybrid turn completes (status idle). */
export function hybridPlainChatUntilIdle(
  runId: string,
  text: string,
  agentId: string,
  timeoutMs = 120_000,
): Promise<HybridChatResult> {
  const logs: string[] = [];
  let replyText = '';
  let status = 'running';
  let sawRunning = false;

  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`${WS_BASE}/${runId}`);
    let sent = false;

    const finish = (error?: Error) => {
      clearTimeout(timer);
      try {
        ws.close();
      } catch {
        // already closed
      }
      if (error) reject(error);
      else resolve({ logs, replyText, status });
    };

    const timer = setTimeout(() => {
      finish(new Error(`hybrid websocket timeout (${timeoutMs}ms) run_id=${runId}`));
    }, timeoutMs);

    ws.addEventListener('open', () => {
      ws.send(JSON.stringify({ text, agent_id: agentId }));
      sent = true;
    });

    ws.addEventListener('message', (event) => {
      const payload = JSON.parse(String(event.data)) as {
        event: string;
        data?: Record<string, unknown>;
      };

      if (payload.event === 'log') {
        const line = String((payload.data as { message?: string } | undefined)?.message ?? '');
        if (line) logs.push(line);
      }

      if (payload.event === 'message') {
        const message = (payload.data as { message?: { agent?: string; text?: string } } | undefined)
          ?.message;
        const agent = message?.agent ?? '';
        if (agent && agent !== 'User' && agent !== 'Supervisor') {
          replyText = String(message?.text ?? '');
        }
      }

      if (payload.event === 'state_patch') {
        const patch = (payload.data as { patch?: { status?: string } } | undefined)?.patch;
        if (patch?.status) {
          status = patch.status;
          if (patch.status === 'running') {
            sawRunning = true;
          }
        }
        if (sent && sawRunning && patch?.status === 'idle') {
          finish();
        }
      }
    });

    ws.addEventListener('error', () => {
      finish(new Error(`websocket error run_id=${runId}`));
    });
  });
}
