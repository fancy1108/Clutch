import { describe, expect, it } from 'vitest';
import {
  mergeChatMessages,
  mergeMessageFields,
  createUserChatMessage,
  USER_CHAT_AVATAR,
  shouldPreserveOptimisticRun,
} from './clutchState';
import type { ChatMessage } from '../types';

describe('createUserChatMessage', () => {
  it('uses the shared user avatar', () => {
    const message = createUserChatMessage('hello');
    expect(message.avatar).toBe(USER_CHAT_AVATAR);
  });
});

describe('mergeChatMessages', () => {
  it('keeps optimistic messages when server sends an empty list', () => {
    const optimistic = [createUserChatMessage('draw a cat')];
    expect(mergeChatMessages(optimistic, [])).toEqual(optimistic);
  });

  it('dedupes the same user instruction from server and client', () => {
    const optimistic = [createUserChatMessage('draw a cat')];
    const server: ChatMessage[] = [
      {
        id: 'user_server',
        agent: 'User',
        avatar: '',
        time: '17:00',
        text: 'draw a cat',
      },
    ];
    expect(mergeChatMessages(optimistic, server)).toHaveLength(1);
    expect(mergeChatMessages(optimistic, server)[0].id).toBe(optimistic[0].id);
  });

  it('fills avatar on optimistic user rows when server echoes the same text', () => {
    const optimistic = [{ ...createUserChatMessage('draw a cat'), avatar: '' }];
    const server: ChatMessage[] = [
      {
        id: 'user_server',
        agent: 'User',
        avatar: USER_CHAT_AVATAR,
        time: '17:00',
        text: 'draw a cat',
      },
    ];
    expect(mergeChatMessages(optimistic, server)[0].avatar).toBe(USER_CHAT_AVATAR);
  });

  it('appends new agent messages from the server', () => {
    const optimistic = [createUserChatMessage('draw a cat')];
    const server: ChatMessage[] = [
      ...optimistic,
      {
        id: 'agent_1',
        agent: 'The Artist',
        avatar: '',
        time: '17:01',
        text: '![Generated image](https://example.com/a.png)',
      },
    ];
    const merged = mergeChatMessages(optimistic, server);
    expect(merged).toHaveLength(2);
    expect(merged[1].agent).toBe('The Artist');
  });
});

describe('mergeMessageFields', () => {
  const base: ChatMessage = {
    id: 'agent_hybrid_1',
    agent: 'Claude test Session',
    avatar: '',
    time: '17:01',
    text: '天蝎女很深情。',
    runtimeEngine: 'Claude CLI (Hybrid)',
    rawOutput: 'raw-from-message',
    outputEvents: [
      { type: 'shell_echo', visible: false, content: 'claude -p ...' },
      { type: 'system_prompt', visible: false, content: 'You are Claude' },
    ],
  };

  it('does not let empty outputEvents wipe existing hybrid details', () => {
    const merged = mergeMessageFields(base, { ...base, outputEvents: [] });
    expect(merged.outputEvents).toHaveLength(2);
    expect(merged.rawOutput).toBe('raw-from-message');
  });

  it('prefers non-empty incoming outputEvents', () => {
    const merged = mergeMessageFields(
      { ...base, outputEvents: undefined, rawOutput: undefined },
      {
        ...base,
        outputEvents: [{ type: 'boundary_marker', visible: false, content: '__CLUTCH_DONE_x__' }],
        rawOutput: 'incoming-raw',
      },
    );
    expect(merged.outputEvents).toHaveLength(1);
    expect(merged.rawOutput).toBe('incoming-raw');
  });

  it('keeps rawOutput when incoming patch omits it', () => {
    const merged = mergeMessageFields(base, { ...base, rawOutput: undefined });
    expect(merged.rawOutput).toBe('raw-from-message');
  });
});

describe('shouldPreserveOptimisticRun', () => {
  const userOnly = [createUserChatMessage('hello')];
  const withAgent: ChatMessage[] = [
    ...userOnly,
    {
      id: 'agent_1',
      agent: 'Clutch Agent',
      avatar: '',
      time: '17:01',
      text: 'hi',
    },
  ];

  it('allows plain chat to return idle after assistant reply', () => {
    expect(
      shouldPreserveOptimisticRun(
        {
          run_id: 'run_1',
          workflow_id: '',
          status: 'running',
          messages: userOnly,
        } as import('../types').ClutchState,
        { status: 'idle', messages: withAgent },
      ),
    ).toBe(false);
  });

  it('still preserves workflow optimistic running before agent reply', () => {
    expect(
      shouldPreserveOptimisticRun(
        {
          run_id: 'run_1',
          workflow_id: 'my-flow',
          status: 'running',
          messages: userOnly,
        } as import('../types').ClutchState,
        { status: 'idle' },
      ),
    ).toBe(true);
  });
});
