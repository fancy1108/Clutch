import type { DispatchLaneSession } from '../types';

export interface TerminalHistoryCommand {
  cmd: string;
  descKey: string;
}

/** Clutch lane ids are UUIDs — not valid OpenCode `opencode -s` session ids (ses_*). */
export function isClutchAssignedSessionId(id: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id.trim());
}

export function isOpenCodeNativeSessionId(id: string): boolean {
  const trimmed = id.trim();
  return Boolean(trimmed) && !isClutchAssignedSessionId(trimmed);
}

/** CLIs that receive Clutch lane UUID via --session-id on interactive PTY spawn. */
export function canResumeByStoredSessionId(agentType: string, id: string): boolean {
  const trimmed = id.trim();
  if (!trimmed) return false;
  if (!isClutchAssignedSessionId(trimmed)) return true;
  const tool = agentType.trim().toLowerCase();
  return tool === 'claude-cli'
    || tool === 'claude'
    || tool === 'codebuddy-cli'
    || tool === 'codebuddy'
    || tool === 'cbc';
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
        cmd: id && canResumeByStoredSessionId(tool, id)
          ? wrapResumeCommandWithWorkspaceCd(workspacePath, `claude --resume ${id}`)
          : wrapResumeCommandWithWorkspaceCd(workspacePath, 'claude'),
        descKey:
          'Run this in your system terminal from the same project directory Clutch used. Restores the Claude Code session. If unsure, run claude (no args) or use /resume in the CLI picker.',
      };
    case 'codebuddy-cli':
    case 'codebuddy':
    case 'cbc':
      return {
        cmd: id && canResumeByStoredSessionId(tool, id)
          ? wrapResumeCommandWithWorkspaceCd(workspacePath, `codebuddy --resume ${id}`)
          : wrapResumeCommandWithWorkspaceCd(workspacePath, 'codebuddy'),
        descKey:
          'Run this in your system terminal from the same project directory Clutch used. Restores the CodeBuddy session.',
      };
    case 'codex-cli':
    case 'codex':
      return id && canResumeByStoredSessionId(tool, id)
        ? {
            cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, `codex resume ${id}`),
            descKey:
              'Run this in your system terminal from the same project directory Clutch used. Restores the Codex session by ID.',
          }
        : {
            cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, 'codex resume --last'),
            descKey:
              'Run this in your system terminal from the same project directory Clutch used. Continues the most recent Codex session in that folder (codex resume --last). Run codex resume to pick from history.',
          };
    case 'opencode-cli':
    case 'opencode':
      return isOpenCodeNativeSessionId(id)
        ? {
            cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, `opencode -s ${id}`),
            descKey:
              'Run this in your system terminal from the same project directory Clutch used. Restores the OpenCode session by ID.',
          }
        : {
            cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, 'opencode -c'),
            descKey:
              'Run this in your system terminal from the same project directory Clutch used. Continues the most recent OpenCode session in that folder (opencode -c). Run opencode session list to pick a specific session.',
          };
    case 'mimo-cli':
    case 'mimo':
      return isOpenCodeNativeSessionId(id)
        ? {
            cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, `mimo -s ${id}`),
            descKey:
              'Run this in your system terminal from the same project directory Clutch used. Restores the MiMo Code session by ID.',
          }
        : {
            cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, 'mimo -c'),
            descKey:
              'Run this in your system terminal from the same project directory Clutch used. Continues the most recent MiMo Code session in that folder (mimo -c). Run mimo session list to pick a specific session.',
          };
    case 'antigravity-cli':
    case 'agy-cli':
    case 'agy':
      return id && canResumeByStoredSessionId(tool, id)
        ? {
            cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, `agy --conversation ${id}`),
            descKey:
              'Run this in your system terminal from the same project directory Clutch used. Restores the Antigravity CLI session.',
          }
        : {
            cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, 'agy'),
            descKey:
              'Run this in your system terminal from the same project directory Clutch used. Open Antigravity CLI and pick the conversation from its session list.',
          };
    case 'rivet-cli':
    case 'rivet':
    case 't9-cli':
      return {
        cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, 'rivet'),
        descKey:
          'Run this in your system terminal from the same project directory. Rivet does not support resuming by session ID — open the TUI and pick the conversation in its session list.',
      };
    case 'aider-cli':
    case 'aider':
      return {
        cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, 'aider'),
        descKey:
          'Run Aider in your system terminal from the same project directory. Aider resumes via chat-history files, not session IDs — start aider and use --restore-chat-history if you saved history.',
      };
    case 'ollama-cli':
    case 'ollama':
      return {
        cmd: wrapResumeCommandWithWorkspaceCd(workspacePath, 'ollama'),
        descKey:
          'Ollama has no session resume by ID. Run ollama in your system terminal from the project directory to continue interacting with the model.',
      };
    case 'zcode-cli':
    case 'zcode':
      return {
        cmd: id && id.startsWith('sess_')
          ? wrapResumeCommandWithWorkspaceCd(workspacePath, `zcode --resume ${id}`)
          : wrapResumeCommandWithWorkspaceCd(workspacePath, 'zcode -c'),
        descKey:
          'Run this in your system terminal from the same project directory Clutch used. Resumes the ZCode session by sess_-prefixed id, or continues the most recent session (zcode -c).',
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
