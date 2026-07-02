import { describe, expect, it } from 'vitest';
import {
  buildTerminalHistoryCommand,
  shellEscapeDoubleQuoted,
  wrapResumeCommandWithWorkspaceCd,
} from './terminalSessionCommands';

describe('buildTerminalHistoryCommand', () => {
  it('builds claude resume command with session id', () => {
    expect(buildTerminalHistoryCommand('claude-cli', 'abc-123')).toEqual({
      cmd: 'claude --resume abc-123',
      descKey:
        'Run this in your system terminal from the same project directory Clutch used. Restores the Claude Code session. If unsure, run claude (no args) or use /resume in the CLI picker.',
    });
  });

  it('prefixes claude resume with cd when workspace path is provided', () => {
    expect(buildTerminalHistoryCommand('claude-cli', 'abc-123', '/Users/fancy/clutch')).toEqual({
      cmd: 'cd "/Users/fancy/clutch" && claude --resume abc-123',
      descKey:
        'Run this in your system terminal from the same project directory Clutch used. Restores the Claude Code session. If unsure, run claude (no args) or use /resume in the CLI picker.',
    });
  });

  it('shell-escapes spaces in workspace path', () => {
    expect(
      buildTerminalHistoryCommand('claude-cli', 'abc-123', '/Users/fancy/My Projects/clutch').cmd,
    ).toBe('cd "/Users/fancy/My Projects/clutch" && claude --resume abc-123');
  });

  it('does not prefix bare claude open command', () => {
    expect(buildTerminalHistoryCommand('claude-cli', '', '/Users/fancy/clutch').cmd).toBe('claude');
  });

  it('builds codex resume command with session id', () => {
    expect(buildTerminalHistoryCommand('codex-cli', 'sid-1')).toEqual({
      cmd: 'codex resume sid-1',
      descKey:
        'Run this in your system terminal from the same project directory Clutch used. Restores the Codex session by ID.',
    });
  });

  it('prefixes codex resume with cd when workspace path is provided', () => {
    expect(buildTerminalHistoryCommand('codex-cli', 'sid-1', '/Users/fancy/clutch').cmd).toBe(
      'cd "/Users/fancy/clutch" && codex resume sid-1',
    );
  });

  it('builds opencode resume command with session id', () => {
    expect(buildTerminalHistoryCommand('opencode-cli', 'sid-2')).toEqual({
      cmd: 'opencode -s sid-2',
      descKey:
        'Run this in your system terminal from the same project directory Clutch used. Restores the OpenCode session by ID.',
    });
  });

  it('prefixes opencode resume with cd when workspace path is provided', () => {
    expect(buildTerminalHistoryCommand('opencode-cli', 'sid-2', '/Users/fancy/clutch').cmd).toBe(
      'cd "/Users/fancy/clutch" && opencode -s sid-2',
    );
  });

  it('builds rivet fallback without resume by id', () => {
    expect(buildTerminalHistoryCommand('rivet-cli', 'sid-3', '/Users/fancy/clutch')).toEqual({
      cmd: 'cd "/Users/fancy/clutch" && rivet',
      descKey:
        'Run this in your system terminal from the same project directory. Rivet does not support resuming by session ID — open the TUI and pick the conversation in its session list.',
    });
  });

  it('builds aider fallback without resume by id', () => {
    expect(buildTerminalHistoryCommand('aider-cli', 'sid-4', '/Users/fancy/clutch').cmd).toBe(
      'cd "/Users/fancy/clutch" && aider',
    );
  });

  it('builds ollama fallback without resume by id', () => {
    expect(buildTerminalHistoryCommand('ollama-cli', 'sid-5', '/Users/fancy/clutch').cmd).toBe(
      'cd "/Users/fancy/clutch" && ollama',
    );
  });
});

describe('shellEscapeDoubleQuoted', () => {
  it('escapes double quotes in path', () => {
    expect(shellEscapeDoubleQuoted('/tmp/a"b')).toBe('"/tmp/a\\"b"');
  });
});

describe('wrapResumeCommandWithWorkspaceCd', () => {
  it('returns command unchanged when workspace is empty', () => {
    expect(wrapResumeCommandWithWorkspaceCd('', 'claude --resume x')).toBe('claude --resume x');
  });
});
