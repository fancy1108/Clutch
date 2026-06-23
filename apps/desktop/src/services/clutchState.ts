import { useSyncExternalStore } from 'react';
import type { ChatMessage, ClutchState, StatePatchData, WebSocketEnvelope } from '../types';

export const DEFAULT_RUN_ID = 'test_run_001';

function createEmptyState(runId: string): ClutchState {
  return {
    run_id: runId,
    workflow_id: 'video-production',
    current_instruction: '',
    active_node_id: '',
    active_agent: 'Orchestrator',
    status: 'running',
    messages: [],
    terminal_logs: [],
    changed_files: [],
  };
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== 'object') return false;
  const msg = value as Record<string, unknown>;
  return typeof msg.id === 'string' && typeof msg.text === 'string';
}

class ClutchStateStore {
  private state: ClutchState = createEmptyState(DEFAULT_RUN_ID);
  private listeners = new Set<() => void>();
  private socket: WebSocket | null = null;
  private connectPromise: Promise<void> | null = null;
  private runId = DEFAULT_RUN_ID;
  private _connected = false;

  get connected(): boolean {
    return this._connected;
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getSnapshot = (): ClutchState => this.state;

  private emit(): void {
    for (const listener of this.listeners) {
      listener();
    }
  }

  private applyPatch(patch: Partial<ClutchState>): void {
    this.state = { ...this.state, ...patch };
    this.emit();
  }

  private appendMessage(message: ChatMessage): void {
    if (this.state.messages.some((item) => item.id === message.id)) return;
    this.applyPatch({ messages: [...this.state.messages, message] });
  }

  private appendLog(line: string): void {
    if (!line || this.state.terminal_logs.at(-1) === line) return;
    this.applyPatch({ terminal_logs: [...this.state.terminal_logs, line] });
  }

  connect(runId: string = DEFAULT_RUN_ID): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN && this.runId === runId) {
      return Promise.resolve();
    }

    if (this.connectPromise) {
      return this.connectPromise;
    }

    this.runId = runId;
    this.connectPromise = new Promise((resolve, reject) => {
      const ws = new WebSocket(`ws://localhost:8123/ws/runs/${runId}`);
      this.socket = ws;

      ws.onopen = () => {
        this._connected = true;
        console.log('%c[Clutch WS] Connected to sidecar', 'color: #22c55e; font-weight: bold;');
        resolve();
      };

      ws.onmessage = (event) => {
        try {
          const envelope = JSON.parse(event.data) as WebSocketEnvelope;
          if (envelope.event === 'state_patch') {
            const data = envelope.data as StatePatchData;
            this.applyPatch(data.patch);
            console.log('%c[Clutch] state_patch', 'color: #22c55e; font-weight: bold;', data.patch);
            return;
          }
          if (envelope.event === 'message') {
            const data = envelope.data as { message?: unknown };
            if (isChatMessage(data.message)) {
              this.appendMessage(data.message);
            }
            return;
          }
          if (envelope.event === 'log') {
            const data = envelope.data as { message?: string };
            if (data.message) {
              this.appendLog(data.message);
            }
          }
        } catch {
          console.warn('[Clutch WS] non-JSON message:', event.data);
        }
      };

      ws.onerror = () => {
        this.connectPromise = null;
        reject(new Error('WebSocket connection failed'));
      };

      ws.onclose = () => {
        this._connected = false;
        this.socket = null;
        this.connectPromise = null;
        this.emit();
      };
    });

    return this.connectPromise;
  }

  async send(payload: Record<string, unknown>): Promise<void> {
    await this.connect(this.runId);
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }
    this.socket.send(JSON.stringify(payload));
  }
}

export const clutchStore = new ClutchStateStore();

export function useClutchState(): { state: ClutchState; connected: boolean } {
  const state = useSyncExternalStore(clutchStore.subscribe, clutchStore.getSnapshot);
  return { state, connected: clutchStore.connected };
}

export const connectSidecarWebSocket = (): Promise<void> => clutchStore.connect(DEFAULT_RUN_ID);

export const sendSidecarTestMessage = async (): Promise<void> => {
  await clutchStore.send({ text: 'Hello sidecar!' });
};

export const submitChatMessage = async (text: string): Promise<void> => {
  await clutchStore.send({ text });
};
