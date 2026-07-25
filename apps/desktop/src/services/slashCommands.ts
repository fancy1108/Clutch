/**
 * Chat slash commands (capability D18) — /plan /compact /todos (+ help).
 * Skills (`/skill:…`) remain separate; this list is shown first in the `/` picker.
 */

export type SlashCommandId = 'plan' | 'compact' | 'todos' | 'help';

export interface SlashCommand {
  id: SlashCommandId;
  /** Typed token without leading slash */
  token: string;
  label: string;
  description: string;
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    id: 'plan',
    token: 'plan',
    label: '/plan',
    description: 'Enter Plan mode (read-only until you switch back)',
  },
  {
    id: 'compact',
    token: 'compact',
    label: '/compact',
    description: 'Compact this chat’s context and show a digest',
  },
  {
    id: 'todos',
    token: 'todos',
    label: '/todos',
    description: 'Focus the current Todo checklist in Chat',
  },
  {
    id: 'help',
    token: 'help',
    label: '/help',
    description: 'List available slash commands',
  },
];

/** Match filter against token or label (case-insensitive). */
export function filterSlashCommands(filter: string): SlashCommand[] {
  const q = filter.trim().toLowerCase();
  if (!q) return SLASH_COMMANDS;
  return SLASH_COMMANDS.filter(
    (c) => c.token.startsWith(q) || c.label.toLowerCase().includes(q),
  );
}

/**
 * If the whole input (trimmed) is exactly `/token` or `/token …`, return the command.
 * Used when the user presses Enter without picking from the popover.
 */
export function matchExactSlashCommand(text: string): SlashCommand | null {
  const trimmed = text.trim();
  if (!trimmed.startsWith('/')) return null;
  const body = trimmed.slice(1);
  if (!body || body.includes(' ') || body.startsWith('skill:')) return null;
  const token = body.toLowerCase();
  return SLASH_COMMANDS.find((c) => c.token === token) ?? null;
}
