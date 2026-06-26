import { describe, expect, it } from 'vitest';
import { mergeChatMessages, createUserChatMessage, USER_CHAT_AVATAR } from './clutchState';
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
