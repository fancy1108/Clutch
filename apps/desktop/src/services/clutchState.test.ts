import { describe, expect, it } from 'vitest';
import {
  mergeChatMessages,
  mergeMessageFields,
  createUserChatMessage,
  USER_CHAT_AVATAR,
  shouldPreserveOptimisticRun,
  preferRicherSessionPatch,
  isAuthoritativeMessageReplacement,
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

  it('appends duplicate user text when a new turn was optimistically queued at the end', () => {
    const pendingId = 'user_pending_turn_2';
    const firstTurn = [
      createUserChatMessage('你好'),
      {
        id: 'agent_1',
        agent: 'Clutch Agent',
        avatar: '',
        time: '17:01',
        text: '你好！',
      },
      { ...createUserChatMessage('你好'), id: pendingId },
    ];
    const server: ChatMessage[] = [
      firstTurn[0],
      firstTurn[1] as ChatMessage,
      {
        id: pendingId,
        agent: 'User',
        avatar: USER_CHAT_AVATAR,
        time: '17:02',
        text: '你好',
      },
    ];
    const merged = mergeChatMessages(firstTurn, server, { pendingUserMessageId: pendingId });
    expect(merged.filter((message) => message.agent === 'User')).toHaveLength(2);
    expect(merged[2].id).toBe(pendingId);
  });

  it('allows a new turn with repeated text when pending user message id is set', () => {
    const pendingId = 'user_client_turn_2';
    const firstTurn = [
      createUserChatMessage('你好'),
      {
        id: 'agent_1',
        agent: 'Clutch Agent',
        avatar: '',
        time: '17:01',
        text: '你好！',
      },
    ];
    const server: ChatMessage[] = [
      {
        id: pendingId,
        agent: 'User',
        avatar: USER_CHAT_AVATAR,
        time: '17:02',
        text: '你好',
      },
    ];
    const merged = mergeChatMessages(firstTurn, server, { pendingUserMessageId: pendingId });
    expect(merged.filter((message) => message.agent === 'User')).toHaveLength(2);
    expect(merged[2].id).toBe(pendingId);
  });

  it('dedupes workflow start server echo while pending id points at optimistic row', () => {
    const optimistic = [createUserChatMessage('design dashboard')];
    const pendingId = optimistic[0].id;
    const server: ChatMessage[] = [
      {
        id: 'user_server',
        agent: 'User',
        avatar: USER_CHAT_AVATAR,
        time: '14:21',
        text: 'design dashboard',
      },
    ];
    const merged = mergeChatMessages(optimistic, server, { pendingUserMessageId: pendingId });
    expect(merged).toHaveLength(1);
    expect(merged[0].id).toBe(pendingId);
  });

  it('dedupes late workflow user echo after the first agent replied', () => {
    const firstTurn = [
      createUserChatMessage('design a dashboard'),
      {
        id: 'agent_1',
        agent: '1-Product Manager',
        avatar: '',
        time: '14:09',
        text: '{"page_goal":"observability"}',
      },
    ];
    const lateEcho: ChatMessage[] = [
      ...firstTurn,
      {
        id: 'user_server',
        agent: 'User',
        avatar: USER_CHAT_AVATAR,
        time: '14:09',
        text: 'design a dashboard',
      },
    ];
    expect(mergeChatMessages(firstTurn, lateEcho)).toHaveLength(2);
  });

  it('allows duplicate user text in new turns when pending user message id is set', () => {
    const pendingId = 'user_server_dup';
    const firstTurn = [
      createUserChatMessage('你好'),
      {
        id: 'agent_1',
        agent: 'Clutch Agent',
        avatar: '',
        time: '17:01',
        text: '你好！',
      },
    ];
    const server: ChatMessage[] = [
      ...firstTurn,
      {
        id: pendingId,
        agent: 'User',
        avatar: USER_CHAT_AVATAR,
        time: '17:02',
        text: '你好',
      },
    ];
    const merged = mergeChatMessages(firstTurn, server, { pendingUserMessageId: pendingId });
    expect(merged.filter((message) => message.agent === 'User')).toHaveLength(2);
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

describe('preferRicherSessionPatch', () => {
  it('keeps hydrated assistant reply when WS reconnect patch is stale', () => {
    const preferred = {
      run_id: 'run_a',
      workflow_id: '',
      status: 'idle',
      messages: [
        createUserChatMessage('hello'),
        {
          id: 'agent_1',
          agent: 'Claude',
          avatar: '',
          time: '17:01',
          text: 'background reply',
        },
      ],
    } as import('../types').ClutchState;

    const patch = preferRicherSessionPatch(preferred, {
      status: 'running',
      messages: [createUserChatMessage('hello')],
    });

    expect(patch.status).toBe('idle');
    expect(patch.messages).toHaveLength(2);
    expect(patch.messages?.[1].text).toBe('background reply');
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

describe('isAuthoritativeMessageReplacement', () => {
  it('detects message deletions from shorter server patches', () => {
    const existing: ChatMessage[] = [
      createUserChatMessage('hello'),
      {
        id: 'agent_1',
        agent: 'Clutch',
        avatar: '',
        time: '12:00',
        text: 'hi there',
      },
    ];
    const incoming = [existing[0]];
    expect(isAuthoritativeMessageReplacement(existing, incoming)).toBe(true);
  });

  it('does not treat appended messages as replacement', () => {
    const existing = [createUserChatMessage('hello')];
    const incoming = [
      ...existing,
      {
        id: 'agent_1',
        agent: 'Clutch',
        avatar: '',
        time: '12:00',
        text: 'hi there',
      },
    ];
    expect(isAuthoritativeMessageReplacement(existing, incoming)).toBe(false);
  });
});
