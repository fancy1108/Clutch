import { connectRunWebSocket } from './ws.js';

/** Seed a plain-chat session via Sidecar HTTP + WebSocket (Node, not WebView). */
export async function seedPlainChatSession(runId: string, text: string): Promise<void> {
  const sessionRes = await fetch('http://127.0.0.1:8123/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId, title: text.slice(0, 80) }),
  });
  if (!sessionRes.ok) {
    throw new Error(`session create failed: ${sessionRes.status}`);
  }

  let sent = false;
  await connectRunWebSocket(runId, {
    timeoutMs: 60_000,
    onOpen: (ws) => {
      ws.send(JSON.stringify({ text }));
      sent = true;
    },
    onMessage: (payload) => {
      if (!sent || payload.event !== 'message') return false;
      const message = payload.data?.message as { agent?: string } | undefined;
      return Boolean(message?.agent && message.agent !== 'User');
    },
  });
}
