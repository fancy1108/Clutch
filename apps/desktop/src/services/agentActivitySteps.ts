/** Parse Chat/MCP ReAct tool-step lines from terminal_logs for live activity UI (capability D46). */

import type { ToolStep, ToolStepKind } from '../types';

export type ParsedToolDetail = {
  target: string;
  body: string | null;
  isError: boolean;
  meta: string | null;
};

/** Prefer a human target (url / query / path / command) over raw args JSON. */
function humanizeDetailTarget(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed.startsWith('{')) return trimmed;
  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>;
    for (const key of ['url', 'uri', 'href', 'query', 'pattern', 'q', 'path', 'file_path', 'command', 'cmd']) {
      const value = parsed[key];
      if (typeof value === 'string' && value.trim()) return value.trim();
    }
  } catch {
    /* keep raw */
  }
  return trimmed;
}

/** Split sidecar detail into target vs result/error body (UI shows labels, not ASCII rules). */
export function parseToolStepDetail(detail?: string | null): ParsedToolDetail {
  const raw = (detail || '').trim();
  if (!raw) return { target: '', body: null, isError: false, meta: null };
  const lines = raw.split('\n');
  const marker = lines.findIndex((line) => /^──\s*(result|error)\b/i.test(line.trim()));
  if (marker < 0) {
    return { target: humanizeDetailTarget(raw), body: null, isError: false, meta: null };
  }
  const header = lines[marker].trim();
  const isError = /^──\s*error\b/i.test(header);
  const meta = /\(([^)]+)\)/.exec(header)?.[1]?.trim() || null;
  const target = humanizeDetailTarget(lines.slice(0, marker).join('\n').trim());
  const body = lines.slice(marker + 1).join('\n').trim() || null;
  return { target, body, isError, meta };
}

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

function hostLabel(url: string): string {
  const raw = url.trim();
  if (!raw) return 'page';
  try {
    const withProto = raw.includes('://') ? raw : `https://${raw}`;
    const parsed = new URL(withProto);
    const host = parsed.hostname.replace(/^www\./, '');
    const leaf = parsed.pathname.replace(/\/$/, '').split('/').filter(Boolean).pop();
    if (leaf && leaf.length < 28) return compact(`${host}/${leaf}`, 44);
    return compact(host || raw, 44);
  } catch {
    return compact(raw, 44);
  }
}

function kindForTool(shortTool: string): ToolStepKind {
  const key = shortTool.toLowerCase().replace(/-/g, '_');
  if (key === 'web_fetch' || key === 'fetch_url' || key === 'browse_page') return 'fetch';
  if (key === 'read_file' || key === 'read_skill' || key.includes('get_file')) return 'read';
  if (key === 'web_search' || key === 'grep' || key.includes('search')) return 'search';
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

  const url = pickString(args, ['url', 'uri', 'href']);

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
    case 'web_fetch':
    case 'fetch_url':
    case 'browse_page':
      return {
        verb: 'Fetched',
        focus: hostLabel(url || path),
        detail: url || path || argsRaw,
      };
    case 'web_search':
    case 'internet_search':
    case 'search_web':
      return {
        verb: 'Searched',
        focus: pattern ? compact(`“${pattern}”`, 40) : 'the web',
        detail: pattern || argsRaw,
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
    case 'todo_write':
    case 'write_todos':
    case 'update_todos': {
      const todos = Array.isArray(args?.todos) ? args!.todos : [];
      const lines: string[] = [];
      let inProgress = '';
      const completed: string[] = [];
      let focus = '';
      for (const item of todos) {
        if (!item || typeof item !== 'object') continue;
        const row = item as Record<string, unknown>;
        const status = String(row.status || 'pending').trim().toLowerCase();
        const content = String(row.content || row.text || '').trim();
        if (!content) continue;
        lines.push(`[${status}] ${content}`);
        if (status === 'in_progress' && !inProgress) inProgress = content;
        else if (status === 'completed') completed.push(content);
        else if (!focus) focus = content;
      }
      const detail = lines.join('\n') || compact(argsRaw, 96);
      if (inProgress) {
        return { verb: 'Todos', focus: `· ${compact(inProgress, 40)}`, detail };
      }
      if (completed.length && completed.length === lines.length) {
        return {
          verb: 'Todos done',
          focus: `· ${compact(completed[completed.length - 1] || '', 36)}`,
          detail,
        };
      }
      if (completed.length) {
        return {
          verb: 'Todos',
          focus: `· ${compact(completed[completed.length - 1] || '', 40)}`,
          detail,
        };
      }
      if (focus) {
        return { verb: 'Todos', focus: `· ${compact(focus, 40)}`, detail };
      }
      return { verb: 'Updated', focus: 'todos', detail };
    }
    case 'propose_plan':
    case 'create_plan': {
      const title = pickString(args, ['title']) || 'Plan';
      return {
        verb: 'Propose plan',
        focus: compact(title, 36),
        detail: compact(argsRaw, 96),
      };
    }
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

/** Live verb_group source: prefer structured pending steps; never replay a prior log wave. */
export function resolveLiveActivitySteps(
  pending: ToolStep[] | undefined | null,
  logs: string[] | undefined | null,
  options?: { awaiting?: boolean },
): ToolStep[] {
  if (pending && pending.length > 0) return pending;
  // Empty/cleared pending = this turn has no tools yet. Falling back to terminal_logs
  // would resurrect the previous turn's Step 1…N wave (ghost "Working" UI).
  if (!options?.awaiting) return [];
  return toolStepsFromActivityLogs(logs, { awaiting: true });
}

function argsJsonForTarget(shortTool: string, target: string): string {
  const trimmed = target.trim();
  if (!trimmed) return '{}';
  if (trimmed.startsWith('{')) return trimmed;
  const key = shortTool.toLowerCase().replace(/-/g, '_');
  if (key.includes('fetch') || trimmed.startsWith('http')) {
    return JSON.stringify({ url: trimmed });
  }
  if (key.includes('search') || key === 'grep') {
    return JSON.stringify({ query: trimmed, pattern: trimmed });
  }
  if (key.includes('run') || key.includes('shell') || key.includes('exec')) {
    return JSON.stringify({ command: trimmed });
  }
  return JSON.stringify({ path: trimmed });
}

/** True when sealed title is the useless "web fetch web_fetch" style. */
export function isGenericToolTitle(title: string, tool: string): boolean {
  const t = (title || '').trim().toLowerCase();
  if (!t) return true;
  const short = shortToolName(tool).toLowerCase().replace(/-/g, '_');
  const spaced = short.replace(/_/g, ' ');
  if (t === spaced || t === short) return true;
  // "web fetch web_fetch" / "web_fetch web_fetch"
  if (t === `${spaced} ${short}` || t === `${short} ${short}`) return true;
  if (t.endsWith(` ${short}`) && t.replace(` ${short}`, '').replace(/_/g, ' ') === spaced) {
    return true;
  }
  return false;
}

export function isTodoWriteTool(tool: string): boolean {
  const short = shortToolName(tool).toLowerCase().replace(/-/g, '_');
  return short === 'todo_write' || short === 'write_todos' || short === 'update_todos';
}

/** Build a readable title from `[status] content` detail lines (Target panel). */
export function titleFromTodoDetail(detail: string | undefined | null): string | null {
  const lines = String(detail || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return null;
  const strip = (line: string) => line.replace(/^\[[^\]]+\]\s*/, '').trim();
  const inProgress = lines.find((line) => /^\[in_progress\]/i.test(line));
  if (inProgress) {
    const content = strip(inProgress);
    return content ? `Todos · ${compact(content, 40)}` : null;
  }
  const completed = lines.filter((line) => /^\[completed\]/i.test(line));
  if (completed.length && completed.length === lines.length) {
    const content = strip(completed[completed.length - 1] || '');
    return content ? `Todos done · ${compact(content, 36)}` : 'Todos done';
  }
  if (completed.length) {
    const content = strip(completed[completed.length - 1] || '');
    return content ? `Todos · ${compact(content, 40)}` : null;
  }
  const first = strip(lines[0] || '');
  return first ? `Todos · ${compact(first, 40)}` : null;
}

function isOpaqueTodoTitle(title: string): boolean {
  const t = (title || '').trim().toLowerCase();
  return (
    /^update\s+\d+\s+todos?$/.test(t) ||
    t === 'update todos' ||
    t === 'updated todos' ||
    t === 'todos'
  );
}

/**
 * Re-humanize legacy sealed steps (wrong kind / "web fetch web_fetch" titles)
 * so collapsed peeks and verb_group headers stay useful.
 */
export function normalizeToolStepForDisplay(step: ToolStep): ToolStep {
  const short = shortToolName(step.tool);
  const kind = kindForTool(short);
  const parsed = parseToolStepDetail(step.detail);
  const needsTitle = isGenericToolTitle(step.title, short);
  let title = step.title;
  if (isTodoWriteTool(short) && (needsTitle || isOpaqueTodoTitle(step.title))) {
    const fromDetail = titleFromTodoDetail(step.detail || parsed.target);
    if (fromDetail) {
      title = fromDetail;
    } else if (needsTitle) {
      const human = humanizeActivityStep(short, argsJsonForTarget(short, parsed.target));
      title = human.focus ? `${human.verb} ${human.focus}` : human.verb;
    }
  } else if (needsTitle) {
    const human = humanizeActivityStep(short, argsJsonForTarget(short, parsed.target));
    title = human.focus ? `${human.verb} ${human.focus}` : human.verb;
  }
  return {
    ...step,
    tool: short,
    kind: kind !== 'other' || step.kind === 'other' ? kind : step.kind,
    title,
    detail: parsed.target
      ? step.detail && step.detail.includes('──')
        ? step.detail
        : parsed.target
      : step.detail,
  };
}

/** Collapse consecutive todo_write noise — sticky Todos card is the SSOT. */
export function collapseRedundantTodoSteps(steps: ToolStep[]): ToolStep[] {
  const out: ToolStep[] = [];
  for (const step of steps) {
    const prev = out[out.length - 1];
    if (prev && isTodoWriteTool(prev.tool) && isTodoWriteTool(step.tool)) {
      out[out.length - 1] = step;
      continue;
    }
    // Collapse identical consecutive fetch/search failures (e.g. 3× google.com/search).
    if (
      prev &&
      prev.tool === step.tool &&
      prev.title === step.title &&
      prev.status === 'failed' &&
      step.status === 'failed'
    ) {
      out[out.length - 1] = step;
      continue;
    }
    out.push(step);
  }
  return out;
}

/**
 * Prepare steps for the process trail.
 * Todo updates are omitted by default — the sticky/sealed Todo card is SSOT
 * and repeating "Update N todos" in the trail is noise.
 */
export function normalizeToolStepsForDisplay(
  steps: ToolStep[],
  opts?: { includeTodos?: boolean },
): ToolStep[] {
  let mapped = collapseRedundantTodoSteps(steps.map(normalizeToolStepForDisplay));
  if (!opts?.includeTodos) {
    mapped = mapped.filter((step) => !isTodoWriteTool(step.tool));
  }
  return mapped;
}

/** One-line focus under the step title (URL / path / query) — no expand needed. */
export function stepFocusLine(step: ToolStep): string {
  const parsed = parseToolStepDetail(step.detail);
  const target = (parsed.target || '').trim();
  if (!target) return '';
  // Prefer first non-empty line; strip todo status tags if any slipped through.
  const first = target.split('\n').map((line) => line.trim()).find(Boolean) || '';
  if (!first) return '';
  // Skip if the title already contains the same focus (avoid duplicate lines).
  const title = (step.title || '').toLowerCase();
  const leaf = first.replace(/^\[[^\]]+\]\s*/, '');
  if (leaf && title.includes(leaf.toLowerCase().slice(0, Math.min(24, leaf.length)))) {
    return '';
  }
  return compact(first, 64);
}

/** Collapsed peek size for sealed messages (Cursor/Grok: a few lines + expand). */
export const TOOL_TRAIL_PEEK = 3;

/** Live turn: show more step lines in-chat (Grok-style process stream). */
export const TOOL_TRAIL_PEEK_LIVE = 8;

/** Prefer index.html when auto-opening a generated page after the agent writes it. */
export function pickPrimaryHtmlPath(paths: string[]): string | null {
  const html = paths.filter((path) => /\.html?$/i.test(path.trim()));
  if (!html.length) return null;
  const index = html.find((path) => /(?:^|[/\\])index\.html?$/i.test(path));
  return index ?? html[html.length - 1] ?? null;
}

/** Mirrors backend `deliverable_intent.py` — decompose need → deliverable kind. */
export type DeliverableKind = 'html' | 'image' | 'video' | 'code' | 'answer' | 'mixed';
export type DeliverableGoal =
  | 'search'
  | 'summarize'
  | 'visualize'
  | 'present'
  | 'implement'
  | 'ask';

const GOAL_PATTERNS: Record<DeliverableGoal, RegExp> = {
  search:
    /搜索|搜一下|查一下|查下|查找|检索|look\s*up|search\s+(for|the)|关于.+的介绍|资料|相关信息/i,
  summarize: /总结|概括|归纳|简介|介绍一下|講講|讲讲|summarize|summary|概述|梳理一下/i,
  visualize:
    /生成图片|画[一张張]|画个|画一|出图|配图|配一张|海报|插画|封面|示意图|视觉|好看的图|一张图|圖像|图像|图片|写真|信息图|資訊圖|可视化|視覺化|图表|圖表|infographic|短视频|短片|视频|片头|动画|动图|\b(image|picture|photo|poster|illustration|cover|video|clip|animation|infographic|chart|diagram)\b|(generate|create|make|draw)\s+(an?\s+)?(image|picture|photo|poster|video|infographic)/i,
  present:
    /\bhtml\b|\.html?\b|网页|落地页|站点页|单页|首页|展示页|介绍页|介绍站|展示站|打开看|能打开|可浏览|做成页|做成一个页|做个页|页面展示|\b(web\s*page|webpage|landing\s*page|static\s*site|single[- ]page)\b/i,
  implement:
    /写[一段]?代码|写个脚本|实现|函数|pytest|单元测试|\b(python|typescript|javascript|rust|go)\b|\b(code|script|function|implement|refactor)\b|跑一下测试|写测试/i,
  ask: /^(什么|什麼|谁|誰|为什么|為什麼|怎么|怎麼|哪|是否|是不是|怎么样|怎麼樣)\b|\b(what|who|why|how|which|is)\b|[?？]\s*$/i,
};

const VIDEO_RE = /短视频|短片|视频|片头|动画|\b(video|clip|animation|mp4)\b/i;

export function decomposeUserGoals(userText: string | null | undefined): Set<DeliverableGoal> {
  const text = (userText || '').trim();
  const goals = new Set<DeliverableGoal>();
  if (!text) return goals;
  (Object.keys(GOAL_PATTERNS) as DeliverableGoal[]).forEach((name) => {
    if (GOAL_PATTERNS[name].test(text)) goals.add(name);
  });
  if (/(做|写|生成).{0,8}介绍/.test(text) && !goals.has('present') && !goals.has('visualize')) {
    goals.add('summarize');
  }
  if (!goals.size) goals.add(text.length < 40 ? 'ask' : 'summarize');
  return goals;
}

export function classifyDeliverableIntent(
  userText: string | null | undefined,
): DeliverableKind {
  const goals = decomposeUserGoals(userText);
  const text = (userText || '').trim();
  const wantsPresent = goals.has('present');
  const wantsVisual = goals.has('visualize');
  const wantsVideo = wantsVisual && VIDEO_RE.test(text);
  const wantsCode = goals.has('implement') && !wantsPresent && !wantsVisual;
  if (wantsPresent && wantsVisual) return 'mixed';
  if (wantsPresent) return 'html';
  if (wantsVideo) return 'video';
  if (wantsVisual) return 'image';
  if (wantsCode) return 'code';
  return 'answer';
}

/** Auto-open browser only when a browsable page/site was inferred from the ask. */
export function wantsBrowserPreview(userText: string | null | undefined): boolean {
  const kind = classifyDeliverableIntent(userText);
  return kind === 'html' || kind === 'mixed';
}

/** @deprecated Use wantsBrowserPreview — kept for older call sites. */
export function userTurnRequestsHtmlPreview(userText: string | null | undefined): boolean {
  return wantsBrowserPreview(userText);
}

const HEADER_NOUN: Record<ToolStepKind, [string, string]> = {
  read: ['file', 'files'],
  fetch: ['page', 'pages'],
  search: ['query', 'queries'],
  list: ['dir', 'dirs'],
  edit: ['edit', 'edits'],
  execute: ['command', 'commands'],
  other: ['tool', 'tools'],
};

const HEADER_VERB_RUNNING: Record<ToolStepKind, string> = {
  read: 'Reading',
  fetch: 'Fetching',
  search: 'Searching',
  list: 'Listing',
  edit: 'Editing',
  execute: 'Running',
  other: 'Using',
};

const HEADER_VERB_DONE: Record<ToolStepKind, string> = {
  read: 'Read',
  fetch: 'Fetched',
  search: 'Searched',
  list: 'Listed',
  edit: 'Edited',
  execute: 'Ran',
  other: 'Used',
};

/** Grok/Cursor fold header: "Fetched 4 pages, Searched 1 query". */
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
  const order: ToolStepKind[] = [
    'read',
    'fetch',
    'search',
    'list',
    'edit',
    'execute',
    'other',
  ];
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
