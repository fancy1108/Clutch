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

  it('builds codex open command without resume flag', () => {
    expect(buildTerminalHistoryCommand('codex-cli', 'sid-1').cmd).toBe('codex');
  });

  it('builds opencode open command', () => {
    expect(buildTerminalHistoryCommand('opencode-cli', 'sid-2').cmd).toBe('opencode');
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
