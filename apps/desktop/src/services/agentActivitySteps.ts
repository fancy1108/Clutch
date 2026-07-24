/** Parse Chat/MCP ReAct tool-step lines from terminal_logs for live activity UI (capability D46). */

import type { ToolStep, ToolStepKind } from '../types';

export type AgentActivityStep = {
  step: number;
  tool: string;
  shortTool: string;
  detail: string;
  /** Human-readable primary label, e.g. "Reading" */
  verb: string;
  /** Secondary focus, e.g. "README.md" */
  focus: string;
};

const STEP_RE =
  /\[(?:CHAT|MCP)\]\s+Step\s+(\d+):\s+(\S+)\s+args=(.*)$/i;
const DONE_RE = /\[(?:CHAT|MCP)\]\s+(?:Builtin )?Tool response length:/i;
const BLOCKED_RE = /\[(?:CHAT|MCP)\]\s+Blocked /i;

function stripStamp(line: string): string {
  const idx = line.indexOf('[CHAT]');
  const idx2 = line.indexOf('[MCP]');
  const start = idx >= 0 ? idx : idx2;
  return start >= 0 ? line.slice(start) : line;
}

function shortToolName(alias: string): string {
  if (alias.includes('__')) {
    return alias.split('__').slice(1).join('__') || alias;
  }
  return alias;
}

function tryParseArgs(raw: string): Record<string, unknown> | null {
  const trimmed = raw.trim();
  if (!trimmed.startsWith('{')) return null;
  try {
    const parsed = JSON.parse(trimmed) as unknown;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function pickString(args: Record<string, unknown> | null, keys: string[]): string {
  if (!args) return '';
  for (const key of keys) {
    const value = args[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return '';
}

function basenamePath(path: string): string {
  const normalized = path.replace(/\\/g, '/');
  const parts = normalized.split('/').filter(Boolean);
  return parts[parts.length - 1] || path;
}

function compact(text: string, max = 48): string {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

function patchFocus(patch: string): { verb: string; focus: string } {
  if (patch.includes('Delete File:')) {
    const name =
      patch.split('Delete File:')[1]?.split('\n')[0]?.trim() || 'file';
    return { verb: 'Deleting', focus: compact(basenamePath(name), 40) };
  }
  if (patch.includes('Create File:')) {
    const name =
      patch.split('Create File:')[1]?.split('\n')[0]?.trim() || 'file';
    return { verb: 'Creating', focus: compact(basenamePath(name), 40) };
  }
  if (patch.includes('Update File:')) {
    const name =
      patch.split('Update File:')[1]?.split('\n')[0]?.trim() || 'file';
    return { verb: 'Editing', focus: compact(basenamePath(name), 40) };
  }
  return { verb: 'Patching', focus: 'workspace' };
}

function kindForTool(shortTool: string): ToolStepKind {
  const key = shortTool.toLowerCase().replace(/-/g, '_');
  if (key === 'read_file' || key.includes('read') || key.includes('get_file')) return 'read';
  if (key === 'grep' || key.includes('search')) return 'search';
  if (key === 'list_dir' || key.includes('list') || key.includes('dir') || key.includes('tree')) {
    return 'list';
  }
  if (
    key.includes('write') ||
    key.includes('edit') ||
    key.includes('patch') ||
    key.includes('delete') ||
    key.includes('replace') ||
    key === 'apply_patch' ||
    key === 'search_replace'
  ) {
    return 'edit';
  }
  if (key.includes('run') || key.includes('shell') || key.includes('exec') || key.includes('command')) {
    return 'execute';
  }
  return 'other';
}

/** Map tool + args to Cursor-like “Reading path” copy. */
export function humanizeActivityStep(
  shortTool: string,
  argsRaw: string,
): { verb: string; focus: string; detail: string } {
  const args = tryParseArgs(argsRaw);
  const path = pickString(args, ['path', 'file_path', 'file', 'target']);
  const pattern = pickString(args, ['pattern', 'query', 'regex']);
  const command = pickString(args, ['command', 'cmd']);
  const patch = pickString(args, ['patch']);

  switch (shortTool) {
    case 'list_dir':
      return {
        verb: 'Listing',
        focus: path ? compact(path, 40) : '.',
        detail: path || '.',
      };
    case 'read_file':
      return {
        verb: 'Reading',
        focus: path ? compact(basenamePath(path), 40) : 'file',
        detail: path || argsRaw,
      };
    case 'grep':
      return {
        verb: 'Searching',
        focus: pattern ? compact(`“${pattern}”`, 40) : 'workspace',
        detail: pattern || argsRaw,
      };
    case 'search_replace':
      return {
        verb: 'Editing',
        focus: path ? compact(basenamePath(path), 40) : 'file',
        detail: path || argsRaw,
      };
    case 'apply_patch': {
      const { verb, focus } = patchFocus(patch);
      return { verb, focus, detail: compact(argsRaw, 96) };
    }
    case 'run_terminal_cmd':
      return {
        verb: 'Running',
        focus: command ? compact(command, 44) : 'shell',
        detail: command || argsRaw,
      };
    default:
      return {
        verb: shortTool.replace(/_/g, ' '),
        focus: path
          ? compact(basenamePath(path), 40)
          : pattern
            ? compact(pattern, 40)
            : command
              ? compact(command, 40)
              : compact(argsRaw, 40),
        detail: compact(argsRaw, 96),
      };
  }
}

export type ParseAgentActivityOptions = {
  maxSteps?: number;
  /** Only parse logs from this index onward. Default: last “Step 1:” wave (current turn). */
  fromIndex?: number;
};

/** Index of the current tool wave (last log line that is Step 1). */
export function findCurrentActivityWaveStart(logs: string[]): number {
  let startAt = 0;
  for (let i = 0; i < logs.length; i++) {
    const line = stripStamp(logs[i]);
    const match = line.match(STEP_RE);
    if (match && Number(match[1]) === 1) {
      startAt = i;
    }
  }
  return startAt;
}

/** Return recent tool steps from terminal logs (oldest → newest among the tail). */
export function parseAgentActivitySteps(
  logs: string[] | undefined | null,
  options?: ParseAgentActivityOptions,
): AgentActivityStep[] {
  const maxSteps = options?.maxSteps ?? 12;
  if (!logs?.length) return [];
  const fromIndex =
    options?.fromIndex !== undefined
      ? Math.max(0, options.fromIndex)
      : findCurrentActivityWaveStart(logs);
  if (fromIndex >= logs.length) return [];
  const found: AgentActivityStep[] = [];
  for (const raw of logs.slice(fromIndex)) {
    const line = stripStamp(raw);
    if (DONE_RE.test(line) || BLOCKED_RE.test(line)) {
      continue;
    }
    const match = line.match(STEP_RE);
    if (!match) continue;
    const tool = match[2];
    const shortTool = shortToolName(tool);
    const argsRaw = match[3] || '';
    const human = humanizeActivityStep(shortTool, argsRaw);
    const next: AgentActivityStep = {
      step: Number(match[1]),
      tool,
      shortTool,
      detail: human.detail,
      verb: human.verb,
      focus: human.focus,
    };
    const prev = found[found.length - 1];
    if (
      prev &&
      prev.shortTool === next.shortTool &&
      prev.focus === next.focus &&
      prev.detail === next.detail
    ) {
      found[found.length - 1] = next;
      continue;
    }
    found.push(next);
  }
  if (found.length <= maxSteps) return found;
  return found.slice(found.length - maxSteps);
}

/** Fallback: convert log-parsed activity into ToolStep for the verb_group UI. */
export function toolStepsFromActivityLogs(
  logs: string[] | undefined | null,
  options?: ParseAgentActivityOptions & { awaiting?: boolean },
): ToolStep[] {
  const parsed = parseAgentActivitySteps(logs, options);
  const last = parsed.length - 1;
  return parsed.map((step, index) => {
    const isLatest = index === last;
    let status: ToolStep['status'] = 'completed';
    if (isLatest) {
      status = options?.awaiting ? 'awaiting' : 'running';
    }
    const title = step.focus ? `${step.verb} ${step.focus}` : step.verb;
    return {
      id: `log_${step.step}_${step.shortTool}_${index}`,
      kind: kindForTool(step.shortTool),
      tool: step.shortTool,
      status,
      title,
      detail: step.detail,
    };
  });
}

const HEADER_NOUN: Record<ToolStepKind, [string, string]> = {
  read: ['file', 'files'],
  search: ['pattern', 'patterns'],
  list: ['dir', 'dirs'],
  edit: ['edit', 'edits'],
  execute: ['command', 'commands'],
  other: ['tool', 'tools'],
};

const HEADER_VERB_RUNNING: Record<ToolStepKind, string> = {
  read: 'Reading',
  search: 'Searching',
  list: 'Listing',
  edit: 'Editing',
  execute: 'Running',
  other: 'Using',
};

const HEADER_VERB_DONE: Record<ToolStepKind, string> = {
  read: 'Read',
  search: 'Searched',
  list: 'Listed',
  edit: 'Edited',
  execute: 'Ran',
  other: 'Used',
};

/** Grok-style fold header: "Read 2 files, Searched 1 pattern". */
export function verbGroupHeaderLabel(steps: ToolStep[]): string {
  if (!steps.length) return '';
  const anyRunning = steps.some(
    (step) => step.status === 'running' || step.status === 'awaiting',
  );
  const verbs = anyRunning ? HEADER_VERB_RUNNING : HEADER_VERB_DONE;
  const counts: Partial<Record<ToolStepKind, number>> = {};
  for (const step of steps) {
    const kind = step.kind in HEADER_NOUN ? step.kind : 'other';
    counts[kind] = (counts[kind] ?? 0) + 1;
  }
  const order: ToolStepKind[] = ['read', 'search', 'list', 'edit', 'execute', 'other'];
  const parts: string[] = [];
  for (const kind of order) {
    const n = counts[kind] ?? 0;
    if (!n) continue;
    const [singular, plural] = HEADER_NOUN[kind];
    parts.push(`${verbs[kind]} ${n} ${n === 1 ? singular : plural}`);
  }
  if (parts.length) return parts.join(', ');
  return anyRunning ? 'Working…' : 'Tools';
}
