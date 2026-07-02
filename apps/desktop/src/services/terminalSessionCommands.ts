import type { DispatchLaneSession } from '../types';

export interface TerminalHistoryCommand {
  cmd: string;
  descKey: string;
}

/** Shell-escape a path for use inside double quotes. */
export function shellEscapeDoubleQuoted(path: string): string {
  return `"${path.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\$/g, '\\$').replace(/`/g, '\\`')}"`;
}

/** Prefix resume commands with cd so Claude Code finds the session in the right project. */
export function wrapResumeCommandWithWorkspaceCd(workspacePath: string | undefined, cmd: string): string {
  const ws = workspacePath?.trim();
  const trimmedCmd = cmd.trim();
  if (!ws || !trimmedCmd) return cmd;
  return `cd ${shellEscapeDoubleQuoted(ws)} && ${trimmedCmd}`;
}

/** Build a copy-paste terminal command to resume or browse CLI session history. */
export function buildTerminalHistoryCommand(
  agentType: string,
  cliSessionId: string,
  workspacePath?: string,
): TerminalHistoryCommand {
  const id = cliSessionId.trim();
  const tool = agentType.trim().toLowerCase();

  switch (tool) {
    case 'claude-cli':
    case 'claude':
      return {
        cmd: id
          ? wrapResumeCommandWithWorkspaceCd(workspacePath, `claude --resume ${id}`)
          : 'claude',
        descKey:
          'Run this in your system terminal from the same project directory Clutch used. Restores the Claude Code session. If unsure, run claude (no args) or use /resume in the CLI picker.',
      };
    case 'codebuddy-cli':
    case 'codebuddy':
    case 'cbc':
      return {
        cmd: id
          ? wrapResumeCommandWithWorkspaceCd(workspacePath, `codebuddy --resume ${id}`)
          : 'codebuddy',
        descKey:
          'Run this in your system terminal from the same project directory Clutch used. Restores the CodeBuddy session.',
      };
    case 'codex-cli':
    case 'codex':
      return {
        cmd: 'codex',
        descKey: 'Open Codex in your system terminal and use its built-in session picker to browse history.',
      };
    case 'opencode-cli':
    case 'opencode':
      return {
        cmd: 'opencode',
        descKey: 'Open OpenCode in your system terminal; browse session history inside the interactive UI.',
      };
    case 'antigravity-cli':
    case 'agy-cli':
    case 'agy':
      return {
        cmd: id
          ? wrapResumeCommandWithWorkspaceCd(workspacePath, `agy --conversation ${id}`)
          : 'agy',
        descKey:
          'Run this in your system terminal from the same project directory Clutch used. Restores the Antigravity CLI session.',
      };
    default:
      return {
        cmd: id || '',
        descKey: 'Open the matching Agent CLI in your system terminal to browse session history.',
      };
  }
}

export function resolveTerminalHistoryWorkspacePath(
  session: DispatchLaneSession,
  fallbackWorkspacePath?: string,
): string | undefined {
  const fromSession = session.workspace_path?.trim();
  if (fromSession) return fromSession;
  const fallback = fallbackWorkspacePath?.trim();
  return fallback || undefined;
}

export function hasTerminalHistoryCommand(session: DispatchLaneSession): boolean {
  return Boolean(session.cli_session_id?.trim() || session.agent_type?.trim());
}
