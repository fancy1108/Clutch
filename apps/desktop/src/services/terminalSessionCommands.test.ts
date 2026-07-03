import { describe, expect, it } from 'vitest';
import {
  buildTerminalHistoryCommand,
  canResumeByStoredSessionId,
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

  it('prefixes bare claude open command with cd when workspace path is provided', () => {
    expect(buildTerminalHistoryCommand('claude-cli', '', '/Users/fancy/clutch').cmd).toBe(
      'cd "/Users/fancy/clutch" && claude',
    );
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

  it('builds opencode resume command with native session id', () => {
    expect(buildTerminalHistoryCommand('opencode-cli', 'ses_abc123')).toEqual({
      cmd: 'opencode -s ses_abc123',
      descKey:
        'Run this in your system terminal from the same project directory Clutch used. Restores the OpenCode session by ID.',
    });
  });

  it('uses codex resume --last when session id is a Clutch-assigned UUID', () => {
    expect(
      buildTerminalHistoryCommand(
        'codex-cli',
        '4bc4a401-b9db-429e-a11e-49c312651dc7',
        '/Users/fancy/ECC',
      ).cmd,
    ).toBe('cd "/Users/fancy/ECC" && codex resume --last');
  });

  it('uses codex resume with native session id', () => {
    expect(buildTerminalHistoryCommand('codex-cli', '7f9f9a2e-1b3c-4c7a-9b0e-example-id').cmd).toBe(
      'codex resume 7f9f9a2e-1b3c-4c7a-9b0e-example-id',
    );
  });

  it('allows claude resume with Clutch lane UUID', () => {
    expect(canResumeByStoredSessionId('claude-cli', '4bc4a401-b9db-429e-a11e-49c312651dc7')).toBe(true);
    expect(canResumeByStoredSessionId('codex-cli', '4bc4a401-b9db-429e-a11e-49c312651dc7')).toBe(false);
  });

  it('uses opencode -c when session id is a Clutch-assigned UUID', () => {
    expect(
      buildTerminalHistoryCommand(
        'opencode-cli',
        '4bc4a401-b9db-429e-a11e-49c312651dc7',
        '/Users/fancy/ECC',
      ),
    ).toEqual({
      cmd: 'cd "/Users/fancy/ECC" && opencode -c',
      descKey:
        'Run this in your system terminal from the same project directory Clutch used. Continues the most recent OpenCode session in that folder (opencode -c). Run opencode session list to pick a specific session.',
    });
  });

  it('uses agy without conversation id when session id is a Clutch-assigned UUID', () => {
    expect(
      buildTerminalHistoryCommand('antigravity-cli', '4bc4a401-b9db-429e-a11e-49c312651dc7', '/Users/fancy/ECC'),
    ).toEqual({
      cmd: 'cd "/Users/fancy/ECC" && agy',
      descKey:
        'Run this in your system terminal from the same project directory Clutch used. Open Antigravity CLI and pick the conversation from its session list.',
    });
  });

  it('prefixes opencode resume with cd when workspace path is provided', () => {
    expect(buildTerminalHistoryCommand('opencode-cli', 'ses_xyz', '/Users/fancy/clutch').cmd).toBe(
      'cd "/Users/fancy/clutch" && opencode -s ses_xyz',
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
