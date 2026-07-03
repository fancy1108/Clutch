import { describe, expect, it } from 'vitest';
import type { PtyOutputData, PtySessionStatusData } from '../types';

describe('pty websocket payloads', () => {
  it('accepts pty_output shape', () => {
    const data: PtyOutputData = {
      run_id: 'run_1',
      chunk: 'hello',
      encoding: 'utf8',
    };
    expect(data.chunk).toBe('hello');
  });

  it('accepts pty_session_status shape', () => {
    const data: PtySessionStatusData = {
      run_id: 'run_1',
      status: 'ready',
    };
    expect(data.status).toBe('ready');
  });
});
