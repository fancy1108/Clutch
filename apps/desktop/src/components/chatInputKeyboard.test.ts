import { describe, expect, it } from 'vitest';
import { shouldSubmitChatOnEnter } from '../components/chatInputKeyboard';

describe('shouldSubmitChatOnEnter', () => {
  it('submits on plain Enter', () => {
    expect(
      shouldSubmitChatOnEnter(
        { key: 'Enter', shiftKey: false, altKey: false, ctrlKey: false, metaKey: false },
        false,
      ),
    ).toBe(true);
  });

  it('does not submit on Shift+Enter', () => {
    expect(
      shouldSubmitChatOnEnter(
        { key: 'Enter', shiftKey: true, altKey: false, ctrlKey: false, metaKey: false },
        false,
      ),
    ).toBe(false);
  });

  it('does not submit while IME composing', () => {
    expect(
      shouldSubmitChatOnEnter(
        { key: 'Enter', shiftKey: false, altKey: false, ctrlKey: false, metaKey: false },
        true,
      ),
    ).toBe(false);
  });
});
