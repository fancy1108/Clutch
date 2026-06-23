const WS_BASE = 'ws://127.0.0.1:8123/ws/runs';

export type WsEnvelope = {
  event: string;
  data?: Record<string, unknown>;
};

type ConnectOptions = {
  onOpen?: (ws: WebSocket) => void;
  onMessage?: (payload: WsEnvelope) => boolean | void;
  timeoutMs?: number;
};

/** Node-native WebSocket client — avoids launching Chromium for API-only tests. */
export function connectRunWebSocket(runId: string, options: ConnectOptions): Promise<void> {
  const { onOpen, onMessage, timeoutMs = 60_000 } = options;

  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`${WS_BASE}/${runId}`);
    let settled = false;

    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        ws.close();
      } catch {
        // already closed
      }
      if (error) reject(error);
      else resolve();
    };

    const timer = setTimeout(() => {
      finish(new Error(`websocket timeout (${timeoutMs}ms)`));
    }, timeoutMs);

    ws.addEventListener('open', () => {
      onOpen?.(ws);
    });

    ws.addEventListener('message', (event) => {
      const payload = JSON.parse(String(event.data)) as WsEnvelope;
      if (onMessage?.(payload)) {
        finish();
      }
    });

    ws.addEventListener('error', () => {
      finish(new Error('websocket error'));
    });

    ws.addEventListener('close', (event) => {
      if (!settled && event.code !== 1000) {
        finish(new Error(`websocket closed (${event.code})`));
      }
    });
  });
}
