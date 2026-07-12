import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  type OnNodesChange,
  MarkerType,
  applyNodeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  ArrowUp,
  Check,
  Code2,
  FileText,
  ChevronDown,
  ChevronRight,
  Globe,
  History,
  ImagePlus,
  Loader2,
  Mic,
  Monitor,
  Palette,
  Pencil,
  Plus,
  Smartphone,
  Sparkles,
  X,
} from 'lucide-react';
import { useLanguage } from '../LanguageContext';
import { BTN_PRIMARY, BTN_SECONDARY, BTN_SUCCESS } from '../ui/buttonStyles';
import { APP_INPUT_DOCK_BOTTOM_PX } from '../../constants/layout';
import {
  approveDesignPrototype,
  approveDesignReact,
  designScreenVersionPath,
  ensureDesignSession,
  generateDesignReact,
  generateDesignSession,
  getDesignScreenHtml,
  getDesignSession,
  iterateDesignSession,
  parseDesignRounds,
  sendDesignToCoding,
  startDesignPreview,
  stopDesignPreview,
  stripDesignIterateMeta,
  versionedDesignScreenId,
  type CodingHandoff,
  type DesignRound,
  type DesignSession,
  type DesignSpec,
} from '../../services/designApi';
import { clutchStore } from '../../services/clutchState';
import { sidecarAuthedHttpUrl } from '../../services/sidecarUrl';

type DesignWorkspaceProps = {
  runId: string;
  workspaceReady: boolean;
  modelLabel?: string;
  onOpenModels?: () => void;
  onSendToCoding: (handoff: CodingHandoff) => void;
  onSessionTitle?: (title: string, meta?: { device?: 'web' | 'app' }) => void;
  /** Sidebar spinner: true while generating / iterating. */
  onBusyChange?: (busy: boolean, meta?: { device?: 'web' | 'app' }) => void;
};

type SpecData = {
  phase: 'placeholder' | 'ready';
  spec?: DesignSpec | null;
  label?: string;
};
type UiData = {
  phase: 'placeholder' | 'drawing' | 'ready';
  name: string;
  html?: string;
  /** Versioned sidecar iframe src for round history preview. */
  previewSrc?: string | null;
  label?: string;
  screenId?: string;
  device?: 'web' | 'app';
  pickMode?: boolean;
  selectedElementPath?: string | null;
  selectedElementLabel?: string | null;
  onElementPicked?: (payload: { path: string; label: string }) => void;
  onTogglePick?: () => void;
};

type IteratePending = {
  mode: 'modify' | 'add';
  screenId?: string | null;
};

function stripIterateMeta(text: string): string {
  return stripDesignIterateMeta(text);
}

function roundTabLabel(prompt: string, index: number): string {
  const trimmed = prompt.trim();
  const label = `Round ${index + 1}`;
  if (!trimmed) return label;
  const snippet = trimmed.length > 32 ? `${trimmed.slice(0, 32)}…` : trimmed;
  return `${label}: ${snippet}`;
}

function DesignRoundSelector({
  rounds,
  selectedRoundIndex,
  onSelect,
}: {
  rounds: DesignRound[];
  selectedRoundIndex: number;
  onSelect: (index: number) => void;
}) {
  const { t } = useLanguage();
  if (rounds.length <= 1) return null;
  return (
    <div
      className="pointer-events-auto mx-auto flex w-full max-w-3xl items-center gap-2 rounded-2xl border border-outline-variant/30 bg-white/92 px-2.5 py-2 shadow-md backdrop-blur-md"
      data-testid="design-round-selector"
    >
      <span className="inline-flex shrink-0 items-center gap-1 px-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
        <History size={12} />
        {t('Rounds')}
      </span>
      <div className="flex min-w-0 flex-1 gap-1 overflow-x-auto pb-0.5">
        {rounds.map((round) => {
          const active = round.index === selectedRoundIndex;
          return (
            <button
              key={round.index}
              type="button"
              title={round.user_prompt || `Round ${round.index}`}
              onClick={() => onSelect(round.index)}
              className={`shrink-0 rounded-full border px-3 py-1 text-[11px] font-medium transition-colors ${
                active
                  ? 'border-neutral-900 bg-neutral-900 text-white shadow-sm'
                  : 'border-neutral-200 bg-neutral-50 text-neutral-600 hover:border-neutral-300 hover:bg-white'
              }`}
              data-testid={`design-round-tab-${round.index}`}
            >
              {roundTabLabel(round.user_prompt, round.index)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

type AgentLogData = {
  round: DesignRound | null;
  fallbackPrompt?: string;
};

function formatDesignTokenTag(entry: {
  usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number };
  usage_estimated?: boolean;
}): string | null {
  const usage = entry.usage;
  if (!usage) return null;
  const total = Number(usage.total_tokens || 0);
  const input = Number(usage.input_tokens || 0);
  const output = Number(usage.output_tokens || 0);
  if (total <= 0 && input <= 0 && output <= 0) return null;
  const n = total > 0 ? total : input + output;
  const compact =
    n >= 10_000 ? `${Math.round(n / 1000)}k` : n >= 1000 ? `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k` : String(n);
  return entry.usage_estimated ? `~${compact}` : compact;
}

function designModelLabel(entry: { model_name?: string; model_id?: string }): string | null {
  const raw = (entry.model_name || entry.model_id || '').trim();
  if (!raw) return null;
  // Prefer human label; collapse long ids like agnes-2.0-flash → Agnes 2.0 Flash when needed.
  if (!raw.includes('-') || /\s/.test(raw)) return raw;
  return raw
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => (/^\d/.test(part) ? part : part.charAt(0).toUpperCase() + part.slice(1)))
    .join(' ');
}

function AgentLogCardNode({ data }: NodeProps) {
  const { t } = useLanguage();
  const d = data as AgentLogData;
  const [reasoningOpen, setReasoningOpen] = useState(true);
  const round = d.round;
  const hasReasoning = Boolean(round?.reasoning_content?.trim());
  // Skip standalone model/tokens meta lines — those belong as tags on each step.
  const executionEntries = (round?.entries || []).filter(
    (e) => e.text?.trim() && e.kind !== 'model' && e.kind !== 'tokens',
  );
  if (!hasReasoning && executionEntries.length === 0 && !d.fallbackPrompt) {
    return (
      <div className="w-[272px] rounded-2xl border border-outline-variant/30 bg-white/94 p-3 shadow-md">
        <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
        <p className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">
          {t('Agent log')}
        </p>
      </div>
    );
  }

  return (
    <div
      className="flex max-h-[min(520px,70vh)] w-[272px] flex-col overflow-hidden rounded-2xl border border-outline-variant/30 bg-white/94 shadow-md backdrop-blur-md"
      data-testid="design-agent-log-rail"
    >
      <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
      <div className="border-b border-neutral-100 px-3 py-2">
        <p className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">
          {t('Agent log')}
        </p>
        <p className="mt-0.5 line-clamp-2 text-[11px] font-medium text-neutral-700">
          {round?.user_prompt || d.fallbackPrompt || `${t('Round')} ${(round?.index ?? 0) + 1}`}
        </p>
      </div>
      <div className="nodrag nowheel min-h-0 flex-1 space-y-2 overflow-y-auto px-3 py-2.5">
        {hasReasoning ? (
          <div className="overflow-hidden rounded-xl border border-violet-100 bg-violet-50/60">
            <button
              type="button"
              className="flex w-full items-center justify-between gap-2 px-2.5 py-2 text-left"
              onClick={() => setReasoningOpen((v) => !v)}
              aria-expanded={reasoningOpen}
            >
              <span className="text-[10px] font-bold uppercase tracking-wide text-violet-600">
                {t('Thinking process')}
              </span>
              {reasoningOpen ? (
                <ChevronDown size={14} className="shrink-0 text-violet-500" />
              ) : (
                <ChevronRight size={14} className="shrink-0 text-violet-500" />
              )}
            </button>
            {reasoningOpen ? (
              <pre className="max-h-40 overflow-auto whitespace-pre-wrap border-t border-violet-100/80 bg-[#0f1117] px-2.5 py-2 font-mono text-[10px] leading-relaxed text-emerald-300/95">
                {round?.reasoning_content}
              </pre>
            ) : null}
          </div>
        ) : null}
        {executionEntries.length > 0 ? (
          <div className="space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wide text-neutral-400">
              {t('Execution')}
            </p>
            {executionEntries.map((entry, i) => {
              const tokenTag = formatDesignTokenTag(entry);
              const modelTag = designModelLabel(entry);
              const statusLabel =
                entry.status && entry.status !== 'info' ? entry.status : null;
              const showMeta = Boolean(statusLabel || modelTag || tokenTag);
              const usageTitle = entry.usage
                ? `${(entry.usage.input_tokens ?? 0).toLocaleString()} in / ${(entry.usage.output_tokens ?? 0).toLocaleString()} out${
                    entry.usage_estimated ? ' (estimated)' : ''
                  }`
                : undefined;
              return (
                <div
                  key={`${entry.at || ''}-${i}`}
                  className="rounded-lg border border-neutral-100 bg-neutral-50/90 px-2.5 py-2"
                >
                  <p className="whitespace-pre-wrap text-[11px] leading-relaxed text-neutral-700">
                    {entry.text}
                  </p>
                  {showMeta ? (
                    <div className="mt-1.5 flex items-center gap-1.5 overflow-hidden">
                      {statusLabel ? (
                        <span className="shrink-0 text-[10px] font-medium text-neutral-400">
                          {statusLabel}
                        </span>
                      ) : null}
                      <div className="ml-auto flex min-w-0 max-w-full items-center gap-1 overflow-hidden">
                        {modelTag ? (
                          <span
                            className="min-w-0 truncate rounded bg-sky-50 px-1.5 py-px text-[10px] font-medium leading-4 text-sky-700 ring-1 ring-inset ring-sky-200/70"
                            title={entry.model_id || modelTag}
                          >
                            {modelTag}
                          </span>
                        ) : null}
                        {tokenTag ? (
                          <span
                            className="shrink-0 rounded bg-amber-50 px-1.5 py-px font-mono text-[10px] font-medium leading-4 text-amber-800 ring-1 ring-inset ring-amber-200/70"
                            title={usageTitle}
                          >
                            {tokenTag}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function inferIterateModeClient(instruction: string, kind: string | undefined): 'modify' | 'add' {
  const text = instruction.toLowerCase();
  const addKeys = ['新增', '添加一', '再做', '另一个', '新页面', '新画板', 'another', 'new page', 'new screen', 'create a new'];
  if (addKeys.some((k) => text.includes(k))) return 'add';
  if (kind === 'ui' || !kind) return 'modify';
  return 'add';
}

type CanvasSelection = {
  nodeId: string;
  kind: 'ui' | 'spec' | 'md' | 'image' | 'url' | 'agentLog';
  label: string;
  screenId?: string;
};

type ElementSelection = {
  path: string;
  label: string;
  screenId?: string;
};

/** Injected into UI iframe: pick mode + persistent element highlight. */
function buildInteractionScript(opts: {
  pickMode: boolean;
  selectedPath?: string | null;
}): string {
  const pick = opts.pickMode ? 'true' : 'false';
  const pathJson = JSON.stringify(opts.selectedPath || '');
  return `
<script data-clutch-design-interaction="1">
(function(){
  var PICK = ${pick};
  var SELECTED = ${pathJson};
  var last = null;
  var STYLE_ID = '__clutchPickStyle';
  function ensureStyle(){
    if (document.getElementById(STYLE_ID)) return;
    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = [
      '.__clutch-el-hover{outline:1px dashed #38bdf8 !important;outline-offset:2px !important;cursor:crosshair !important;}',
      '.__clutch-el-selected{outline:2px solid #2563eb !important;outline-offset:2px !important;box-shadow:0 0 0 4px rgba(37,99,235,0.25) !important;position:relative;z-index:5;}',
      '.__clutch-el-selected::after{content:attr(data-clutch-label);position:absolute;left:0;top:-18px;background:#2563eb;color:#fff;font:600 10px/1.2 system-ui,sans-serif;padding:2px 6px;border-radius:4px;white-space:nowrap;pointer-events:none;z-index:6;}'
    ].join('');
    document.head.appendChild(s);
  }
  function indexPath(el){
    var parts = [];
    var cur = el;
    while (cur && cur.nodeType === 1 && cur !== document.documentElement) {
      var parent = cur.parentElement;
      if (!parent) break;
      var idx = Array.prototype.indexOf.call(parent.children, cur);
      parts.unshift(String(idx));
      cur = parent;
      if (cur === document.body) break;
    }
    return parts.join('/');
  }
  function elFromIndexPath(path){
    if (!path) return null;
    var parts = String(path).split('/');
    var el = document.body;
    for (var i = 0; i < parts.length; i++) {
      var n = parseInt(parts[i], 10);
      if (!el || !el.children || isNaN(n) || n < 0 || n >= el.children.length) return null;
      el = el.children[n];
    }
    return el;
  }
  function labelFor(el){
    if (!el) return 'element';
    var tag = (el.tagName || 'el').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') {
      var lab = '';
      if (el.id) {
        var byFor = document.querySelector('label[for=\"' + el.id.replace(/\"/g,'') + '\"]');
        if (byFor) lab = (byFor.innerText || '').trim();
      }
      if (!lab && el.closest) {
        var wrap = el.closest('label');
        if (wrap) lab = (wrap.innerText || '').trim().split('\\n')[0];
      }
      var hint = lab || el.getAttribute('placeholder') || el.getAttribute('name') || el.getAttribute('aria-label') || el.type || tag;
      return tag + ': ' + String(hint).slice(0, 40);
    }
    var t = (el.getAttribute('aria-label') || el.innerText || el.getAttribute('alt') || tag).trim();
    return tag + (t && t !== tag ? ': ' + t.slice(0, 40) : '');
  }
  function clearSelected(){
    var prev = document.querySelectorAll('.__clutch-el-selected');
    for (var i = 0; i < prev.length; i++) {
      prev[i].classList.remove('__clutch-el-selected');
      prev[i].removeAttribute('data-clutch-label');
    }
  }
  function applySelected(el, label){
    clearSelected();
    if (!el) return;
    ensureStyle();
    el.classList.add('__clutch-el-selected');
    el.setAttribute('data-clutch-label', label || labelFor(el));
    last = el;
    try { el.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch(_){}
  }
  ensureStyle();
  if (SELECTED) {
    var restored = elFromIndexPath(SELECTED);
    if (restored) applySelected(restored, labelFor(restored));
  }
  if (!PICK) return;
  document.addEventListener('click', function(e){
    e.preventDefault();
    e.stopPropagation();
    var el = e.target;
    if (!el || el === document.documentElement || el === document.body) return;
    var path = indexPath(el);
    var label = labelFor(el);
    applySelected(el, label);
    parent.postMessage({
      source: 'clutch-design-pick',
      path: path,
      label: label
    }, '*');
  }, true);
  document.addEventListener('mouseover', function(e){
    var el = e.target;
    if (!el || el === document.documentElement || el === last) return;
    el.classList.add('__clutch-el-hover');
  }, true);
  document.addEventListener('mouseout', function(e){
    var el = e.target;
    if (el) el.classList.remove('__clutch-el-hover');
  }, true);
})();
</script>
`;
}

function stripInteractionScript(html: string): string {
  return html.replace(
    /<script[^>]*data-clutch-design-interaction="1"[^>]*>[\s\S]*?<\/script>/gi,
    '',
  );
}

/** Ensure srcDoc HTML has <meta charset="utf-8"> to prevent garbled text. */
function ensureCharset(html: string): string {
  if (!html) return html;
  // Already has charset declaration — skip.
  if (/charset\s*=/i.test(html)) return html;
  // Inject right after <head> if present, otherwise after <!doctype …> or at start.
  if (/<head[^>]*>/i.test(html)) {
    return html.replace(/(<head[^>]*>)/i, '$1<meta charset="utf-8"/>');
  }
  if (/<!doctype/i.test(html)) {
    return html.replace(/(<!doctype[^>]*>)/i, '$1<meta charset="utf-8"/>');
  }
  return '<meta charset="utf-8"/>' + html;
}

function withPickerScript(
  html: string,
  opts: boolean | { pickMode?: boolean; selectedPath?: string | null },
): string {
  if (!html) return html;
  const pickMode = typeof opts === 'boolean' ? opts : Boolean(opts.pickMode);
  const selectedPath = typeof opts === 'boolean' ? null : opts.selectedPath || null;
  if (!pickMode && !selectedPath) {
    return stripInteractionScript(html);
  }
  const cleaned = stripInteractionScript(html);
  const script = buildInteractionScript({ pickMode, selectedPath });
  if (cleaned.includes('</body>')) {
    return cleaned.replace('</body>', `${script}</body>`);
  }
  return `${cleaned}${script}`;
}

function selectionKindFromNodeId(id: string): CanvasSelection['kind'] {
  if (id === 'spec') return 'spec';
  if (id === 'mdDoc') return 'md';
  if (id === 'reference') return 'image';
  if (id === 'urlCard') return 'url';
  if (id === 'agentLog') return 'agentLog';
  if (id.startsWith('ui')) return 'ui';
  return 'spec';
}

function selectionLabel(kind: CanvasSelection['kind'], node: Node, session: DesignSession | null): string {
  if (kind === 'spec') return String(session?.spec?.name || 'Design system');
  if (kind === 'md') return session?.reference_md_name || 'DESIGN.md';
  if (kind === 'image') return 'image.png';
  if (kind === 'url') return session?.url_snapshot?.host || session?.reference_url || 'Website';
  if (kind === 'agentLog') return 'Agent log';
  if (kind === 'ui') {
    const data = node.data as UiData;
    return data.name || 'Interface';
  }
  return 'Design system';
}
type RefData = { name: string; url: string };
type MdDocData = { name: string; text: string };
type UrlCardData = {
  url: string;
  host?: string;
  title?: string;
  description?: string;
};

const IN_FLIGHT = new Set(['crafting_spec', 'generating_ui', 'iterating']);

const DESIGN_SYSTEM_PRESETS = [
  {
    id: 'clutch',
    labelKey: 'Clutch',
    descriptionKey: 'Built-in Clutch design system — clean developer-tool aesthetic',
  },
] as const;

type DesignSystemId = (typeof DESIGN_SYSTEM_PRESETS)[number]['id'];

/** Empty session → welcome prompt; never treat `draft` as in-flight canvas work. */
function isWelcomeSession(next: DesignSession): boolean {
  const hasArtifacts = Boolean(next.spec || (next.screens && next.screens.length > 0));
  const hasPrompt = Boolean(next.prompt?.trim());
  if (hasArtifacts || hasPrompt) return false;
  if (IN_FLIGHT.has(next.status)) return false;
  return next.status === 'draft' || next.phase === 'welcome' || !next.status;
}

function hostFromUrl(url: string): string {
  try {
    return new URL(url.includes('://') ? url : `https://${url}`).hostname;
  } catch {
    return url.replace(/^https?:\/\//, '').split('/')[0] || url;
  }
}

function autoPromptForMd(fileName: string): string {
  return `使用 the file [${fileName}] 创建设计系统。设计一个登录页面。`;
}

function autoPromptForUrl(): string {
  return '参考这个网站，生成一个登录页面';
}

/** Design target viewports (CSS px) and canvas preview frames. */
const DEVICE_VIEW = {
  web: {
    designW: 1920,
    designH: 1080,
    /** Canvas preview frame (scaled 1920×1080 @ 0.375) */
    frameW: 720,
    frameH: 405,
  },
  app: {
    designW: 390,
    designH: 844,
    /** Canvas preview frame (scaled phone) */
    frameW: 300,
    frameH: 650,
  },
} as const;

function deviceView(device?: string) {
  return device === 'app' ? DEVICE_VIEW.app : DEVICE_VIEW.web;
}

/** One-row canvas: Agent Log → Spec → Interface (Y aligned). Sync with orchestrator layout. */
const DESIGN_CANVAS_ORIGIN = 40;
const DESIGN_AGENT_LOG_W = 272;
const DESIGN_SPEC_W = 300;
const DESIGN_SOURCE_W = 300;
const DESIGN_CARD_GAP = 48;
const DESIGN_SPEC_UI_GAP = 56;
const DESIGN_ROW_Y = 56;

/** Agent Log | Source/Image | Spec | Interface — fixed row, no overlap. */
const LAYOUT = {
  agentLog: { x: DESIGN_CANVAS_ORIGIN, y: DESIGN_ROW_Y },
  /** Column 2: image / md / url reference card — same row as Agent Log */
  reference: { x: DESIGN_CANVAS_ORIGIN + DESIGN_AGENT_LOG_W + DESIGN_CARD_GAP, y: DESIGN_ROW_Y },
  /** After agent log: 40 + 272 + 48 = 360 */
  source: { x: DESIGN_CANVAS_ORIGIN + DESIGN_AGENT_LOG_W + DESIGN_CARD_GAP, y: DESIGN_ROW_Y },
  /** Spec when no source card */
  spec: { x: DESIGN_CANVAS_ORIGIN + DESIGN_AGENT_LOG_W + DESIGN_CARD_GAP, y: DESIGN_ROW_Y },
  /** Spec when source occupies column 2: 360 + 300 + 48 = 708 */
  specAfterSource: {
    x: DESIGN_CANVAS_ORIGIN + DESIGN_AGENT_LOG_W + DESIGN_CARD_GAP + DESIGN_SOURCE_W + DESIGN_CARD_GAP,
    y: DESIGN_ROW_Y,
  },
} as const;

function uiCanvasPos(specPos: { x: number; y: number }): { x: number; y: number } {
  return {
    x: specPos.x + DESIGN_SPEC_W + DESIGN_SPEC_UI_GAP,
    y: DESIGN_ROW_Y,
  };
}

function ShimmerOverlay() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]">
      <div className="absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-white/55 to-transparent animate-design-shimmer-sweep" />
    </div>
  );
}

function SpecSkeleton() {
  return (
    <div className="space-y-3">
      <div className="h-3 w-24 rounded bg-neutral-200/80 animate-design-skeleton-pulse" />
      <div className="flex gap-1.5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-6 w-6 rounded-md bg-neutral-200/90 animate-design-skeleton-pulse"
            style={{ animationDelay: `${i * 90}ms` }}
          />
        ))}
      </div>
      <div className="space-y-1.5 pt-1">
        <div className="h-2.5 w-full rounded bg-neutral-100 animate-design-skeleton-pulse" />
        <div className="h-2.5 w-4/5 rounded bg-neutral-100 animate-design-skeleton-pulse" />
        <div className="h-2.5 w-3/5 rounded bg-neutral-100 animate-design-skeleton-pulse" />
      </div>
      <div className="flex flex-wrap gap-1.5 pt-1">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-5 w-14 rounded-lg bg-neutral-100 animate-design-skeleton-pulse"
            style={{ animationDelay: `${i * 70}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

function SpecCardNode({ data }: NodeProps) {
  const d = data as SpecData;
  if (d.phase === 'placeholder') {
    return (
      <div className="relative w-[300px] overflow-hidden rounded-2xl border border-indigo-100/80 bg-white p-3.5 shadow-md animate-design-card-in">
        <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
        <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="min-w-0 truncate text-[10px] font-bold uppercase tracking-wider text-indigo-400">
            Design specification
          </p>
          <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-500">
            <Loader2 size={10} className="animate-spin" />
            {d.label || 'Crafting…'}
          </span>
        </div>
        <div className="relative overflow-hidden rounded-xl border border-indigo-50/80 p-3 design-craft-surface">
          <SpecSkeleton />
          <ShimmerOverlay />
        </div>
      </div>
    );
  }

  const spec = d.spec || {};
  const colors = spec.colors || {};
  return (
    <div className="w-[300px] rounded-2xl border border-outline-variant/30 bg-white p-3.5 shadow-md animate-design-card-in">
      <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
      <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
        Design specification
      </p>
      <h3 className="mb-2 text-[14px] font-bold text-neutral-900">{spec.name || 'Spec'}</h3>
      {spec.rationale ? (
        <p className="mb-2.5 text-[11px] leading-relaxed text-neutral-500">{spec.rationale}</p>
      ) : null}
      <div className="space-y-2.5">
        {Object.entries(colors).map(([group, values]) => (
          <div key={group}>
            <p className="mb-1 text-[10px] font-semibold capitalize text-neutral-400">{group}</p>
            <div className="flex flex-wrap gap-1.5">
              {(values || []).map((hex) => (
                <div
                  key={`${group}-${hex}`}
                  className="h-6 w-6 rounded-md border border-black/5 shadow-sm"
                  style={{ background: hex }}
                  title={hex}
                />
              ))}
            </div>
          </div>
        ))}
        {spec.typography?.samples?.length ? (
          <div>
            <p className="mb-1 text-[10px] font-semibold text-neutral-400">Typography</p>
            <div className="space-y-1">
              {spec.typography.samples.map((sample, i) => (
                <p
                  key={i}
                  className="text-neutral-800"
                  style={{
                    fontFamily: spec.typography?.fontFamily,
                    fontSize: sample.size || '13px',
                    fontWeight: Number(sample.weight) || 400,
                  }}
                >
                  Aa · {sample.label}
                </p>
              ))}
            </div>
          </div>
        ) : null}
        {spec.components?.length ? (
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {spec.components.map((c) => (
              <span
                key={c}
                className="rounded-lg border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] text-neutral-600"
              >
                {c}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function UiCardNode({ data, selected }: NodeProps) {
  const { t } = useLanguage();
  const d = data as UiData;
  const view = deviceView(d.device);
  const scale = view.frameW / view.designW;
  const [resolvedPreviewSrc, setResolvedPreviewSrc] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!d.previewSrc || d.pickMode) {
      setResolvedPreviewSrc(null);
      return;
    }
    void sidecarAuthedHttpUrl(d.previewSrc).then((url) => {
      if (!cancelled) setResolvedPreviewSrc(url);
    });
    return () => {
      cancelled = true;
    };
  }, [d.previewSrc, d.pickMode]);

  const useRemotePreview = Boolean(resolvedPreviewSrc) && !d.pickMode;
  if (d.phase === 'placeholder') {
    return (
      <div
        className={`relative overflow-hidden rounded-2xl border border-violet-100/90 bg-white shadow-md animate-design-card-in ${
          selected ? 'ring-2 ring-sky-500 ring-offset-2' : ''
        }`}
        style={{ width: view.frameW }}
      >
        <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
        <div className="flex items-center justify-between gap-2 border-b border-violet-50 px-3 py-2">
          <p className="min-w-0 truncate text-[12px] font-semibold text-neutral-700">{d.name || 'Interface'}</p>
          <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap text-[10px] font-medium text-violet-500">
            <Loader2 size={11} className="animate-spin" />
            {d.label || 'Generating…'}
          </span>
        </div>
        <div
          className="relative overflow-hidden design-craft-surface"
          style={{ height: Math.min(view.frameH, 320) }}
        >
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
            <div className="h-10 w-10 rounded-full border-2 border-violet-200 border-t-violet-500 animate-spin" />
            <p className="text-[12px] font-medium text-violet-500/90">
              {d.label || 'Sketching…'}
            </p>
            <p className="text-[10px] text-neutral-400">
              {d.device === 'app' ? '390 × 844' : '1920 × 1080'}
            </p>
          </div>
          <ShimmerOverlay />
        </div>
      </div>
    );
  }

  const drawing = d.phase === 'drawing';
  const pickMode = Boolean(d.pickMode);
  const hasElement = Boolean(d.selectedElementPath || d.selectedElementLabel);
  // When a component is selected, highlight lives inside the iframe — not the whole artboard.
  const selectedRing = selected
    ? hasElement
      ? 'border-sky-200 shadow-md'
      : 'ring-2 ring-sky-500 ring-offset-2 border-sky-300'
    : 'border-outline-variant/30';
  return (
    <div
      className={`overflow-hidden rounded-2xl border bg-white shadow-md animate-design-card-in ${selectedRing}`}
      style={{ width: view.frameW }}
    >
      <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
      <div className="flex items-center justify-between gap-2 border-b border-neutral-100 px-3 py-2">
        <div className="min-w-0">
          <p className="truncate text-[12px] font-semibold text-neutral-800">{d.name}</p>
          <p className="text-[9px] font-medium uppercase tracking-wide text-neutral-400">
            {d.device === 'app' ? 'Mobile · 390×844' : 'Web · 1920×1080'}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {drawing ? (
            <span className="inline-flex items-center gap-1 whitespace-nowrap text-[10px] font-medium text-violet-500">
              <Loader2 size={11} className="animate-spin" />
              {d.label || 'Generating…'}
            </span>
          ) : (
            <>
              <button
                type="button"
                className={`nodrag nopan inline-flex h-6 w-6 items-center justify-center rounded-md transition-colors ${
                  pickMode
                    ? 'bg-sky-600 text-white'
                    : hasElement
                      ? 'bg-sky-100 text-sky-700'
                      : 'text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700'
                }`}
                title={pickMode ? t('Picking…') : t('Pick element')}
                aria-label={pickMode ? t('Picking…') : t('Pick element')}
                aria-pressed={pickMode}
                onClick={(e) => {
                  e.stopPropagation();
                  d.onTogglePick?.();
                }}
              >
                <Pencil size={12} strokeWidth={2.25} />
              </button>
              {pickMode ? (
                <span className="whitespace-nowrap text-[10px] font-medium text-sky-600">{t('Picking…')}</span>
              ) : hasElement ? (
                <span className="max-w-[120px] truncate whitespace-nowrap text-[10px] font-medium text-sky-700">
                  {d.selectedElementLabel}
                </span>
              ) : (
                <span className="text-[10px] text-emerald-600">Ready</span>
              )}
            </>
          )}
        </div>
      </div>
      <div
        className={`relative overflow-hidden bg-neutral-100 ${
          hasElement && !pickMode ? 'ring-1 ring-inset ring-sky-200' : ''
        }`}
        style={{ width: view.frameW, height: view.frameH }}
      >
        {d.html || resolvedPreviewSrc ? (
          useRemotePreview ? (
            <iframe
              title={d.name}
              src={resolvedPreviewSrc!}
              className={`absolute left-0 top-0 origin-top-left border-0 bg-white pointer-events-none ${
                drawing ? 'animate-design-draw-reveal' : ''
              }`}
              style={{
                width: view.designW,
                height: view.designH,
                transform: `scale(${scale})`,
              }}
            />
          ) : (
            <iframe
              title={d.name}
              srcDoc={ensureCharset(withPickerScript(d.html || '', {
                pickMode,
                selectedPath: d.selectedElementPath,
              }))}
              className={`absolute left-0 top-0 origin-top-left border-0 bg-white ${
                pickMode ? 'pointer-events-auto' : 'pointer-events-none'
              } ${drawing ? 'animate-design-draw-reveal' : ''}`}
              style={{
                width: view.designW,
                height: view.designH,
                transform: `scale(${scale})`,
              }}
            />
          )
        ) : null}
        {drawing ? (
          <>
            <div className="pointer-events-none absolute inset-x-0 top-0 h-1 overflow-hidden">
              <div className="h-full w-1/3 bg-violet-400/80 animate-design-shimmer-sweep" />
            </div>
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/30" />
          </>
        ) : null}
        {pickMode && !hasElement ? (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-sky-600/15 to-transparent px-3 py-2">
            <p className="text-center text-[10px] font-medium text-sky-700">{t('Click a component')}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function RefCardNode({ data }: NodeProps) {
  const d = data as RefData;
  return (
    <div className="w-[300px] overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-md animate-design-card-in">
      <Handle type="target" position={Position.Left} className="!bg-neutral-300" />
      <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
      <div className="flex items-center justify-between border-b border-neutral-100 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <ImagePlus size={14} className="shrink-0 text-amber-500" />
          <p className="truncate text-[12px] font-semibold text-neutral-800">{d.name || 'image.png'}</p>
        </div>
        <span className="shrink-0 text-[10px] text-neutral-400">Reference</span>
      </div>
      <img src={d.url} alt={d.name} className="max-h-[280px] w-full object-contain bg-neutral-50" />
    </div>
  );
}


function MdDocFullModal({ name, text, onClose }: { name: string; text: string; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative mx-4 flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex shrink-0 items-center justify-between gap-2 border-b border-neutral-100 px-4 py-3">
          <div className="flex items-center gap-2">
            <FileText size={14} className="shrink-0 text-neutral-500" />
            <p className="text-[13px] font-semibold text-neutral-800">{name || 'DESIGN.md'}</p>
            <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] text-neutral-500">{text.length.toLocaleString()} chars</span>
          </div>
          <button
            type="button"
            className="rounded-lg p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
        <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap bg-neutral-50 px-4 py-3 font-mono text-[11px] leading-relaxed text-neutral-700">
          {text}
        </pre>
      </div>
    </div>
  );
}

function MdDocCardNode({ data }: NodeProps) {
  const d = data as MdDocData;
  const [showFull, setShowFull] = useState(false);
  return (
    <>
      <div className="w-[300px] overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-md animate-design-card-in">
        <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
        <div className="flex items-center justify-between gap-2 border-b border-neutral-100 px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <FileText size={14} className="shrink-0 text-neutral-500" />
            <p className="truncate text-[12px] font-semibold text-neutral-800">{d.name || 'DESIGN.md'}</p>
          </div>
          <button
            type="button"
            className="nodrag nopan shrink-0 rounded-md border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-neutral-600 hover:bg-neutral-100 hover:text-neutral-800"
            onClick={(e) => { e.stopPropagation(); setShowFull(true); }}
          >
            View full
          </button>
        </div>
        <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap bg-neutral-50/80 px-3 py-2.5 font-mono text-[10px] leading-relaxed text-neutral-600">
          {d.text.slice(0, 3500)}
          {d.text.length > 3500 ? '\n…(truncated — click "View full" to see all)' : ''}
        </pre>
      </div>
      {showFull && <MdDocFullModal name={d.name} text={d.text} onClose={() => setShowFull(false)} />}
    </>
  );
}

function UrlCardNode({ data }: NodeProps) {
  const d = data as UrlCardData;
  const host = d.host || hostFromUrl(d.url);
  return (
    <div className="w-[300px] overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-md animate-design-card-in">
      <Handle type="source" position={Position.Right} className="!bg-neutral-300" />
      <div className="flex items-center gap-2 border-b border-neutral-100 px-3 py-2">
        <Globe size={14} className="shrink-0 text-sky-600" />
        <p className="truncate text-[12px] font-semibold text-neutral-800">{host}</p>
      </div>
      <div className="space-y-2 bg-gradient-to-br from-sky-50/80 to-white px-3 py-3">
        <p className="text-[13px] font-semibold leading-snug text-neutral-900">
          {d.title || host}
        </p>
        {d.description ? (
          <p className="line-clamp-4 text-[11px] leading-relaxed text-neutral-500">{d.description}</p>
        ) : (
          <p className="text-[11px] text-neutral-400">Website reference</p>
        )}
        <a
          href={d.url.startsWith('http') ? d.url : `https://${d.url}`}
          target="_blank"
          rel="noreferrer"
          className="block truncate text-[10px] text-sky-600 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {d.url}
        </a>
      </div>
    </div>
  );
}

const nodeTypes = {
  agentLog: AgentLogCardNode,
  spec: SpecCardNode,
  ui: UiCardNode,
  reference: RefCardNode,
  mdDoc: MdDocCardNode,
  urlCard: UrlCardNode,
};

function FitViewOnNodes({
  layoutKey,
  focusIds,
}: {
  layoutKey: string;
  focusIds?: string[];
}) {
  const { fitView, getNodes } = useReactFlow();
  useEffect(() => {
    if (!layoutKey) return;
    const id = window.setTimeout(() => {
      const all = getNodes();
      const targets =
        focusIds && focusIds.length > 0
          ? all.filter((n) => focusIds.includes(n.id))
          : all;
      void fitView({
        nodes: targets.length > 0 ? targets : undefined,
        padding: focusIds?.length ? 0.35 : 0.22,
        maxZoom: focusIds?.length ? 1.05 : 1,
        minZoom: 0.35,
        duration: 320,
      });
    }, 60);
    return () => window.clearTimeout(id);
  }, [layoutKey, focusIds, fitView, getNodes]);
  return null;
}

function buildCanvasNodes(
  session: DesignSession | null,
  prompt: string,
  drawing: boolean,
  positions: Record<string, { x: number; y: number }>,
  extras?: {
    referenceImageUrl?: string | null;
    referenceMd?: { name: string; text: string } | null;
    referenceUrl?: string | null;
    pickMode?: boolean;
    selectedElementLabel?: string | null;
    selectedElementPath?: string | null;
    pickScreenId?: string | null;
    selectedNodeId?: string | null;
    iteratePending?: IteratePending | null;
    selectedRoundIndex?: number;
    roundHtmlByScreen?: Record<string, string | undefined>;
    runId?: string;
    onElementPicked?: (payload: { path: string; label: string; screenId?: string }) => void;
    onTogglePick?: (payload: { nodeId: string; screenId: string; name: string }) => void;
  },
): Node[] {
  const list: Node[] = [];
  const status = session?.status || 'crafting_spec';
  const rounds = parseDesignRounds(session?.process_log, session?.rounds, session?.round_history);
  const activeRound =
    rounds.find((r) => r.index === extras?.selectedRoundIndex) ?? rounds[rounds.length - 1];
  const showAgentLog =
    Boolean(activeRound) ||
    Boolean(session?.process_log?.length) ||
    IN_FLIGHT.has(status) ||
    Boolean(session?.spec) ||
    Boolean(session?.screens?.length);

  if (showAgentLog) {
    list.push({
      id: 'agentLog',
      type: 'agentLog',
      position: { ...LAYOUT.agentLog },
      data: {
        round: activeRound ?? null,
        fallbackPrompt: session?.prompt || prompt,
      },
      draggable: true,
    });
  }

  const refUrl = extras?.referenceImageUrl || session?.reference_image_url;
  const mdText = extras?.referenceMd?.text || session?.reference_md_text;
  const mdName = extras?.referenceMd?.name || session?.reference_md_name || 'DESIGN.md';
  const refSite = extras?.referenceUrl || session?.reference_url;
  const snap = session?.url_snapshot;

  if (mdText) {
    list.push({
      id: 'mdDoc',
      type: 'mdDoc',
      position: positions.mdDoc || LAYOUT.source,
      data: { name: mdName, text: mdText },
      draggable: true,
    });
  } else if (refSite) {
    list.push({
      id: 'urlCard',
      type: 'urlCard',
      position: positions.urlCard || LAYOUT.source,
      data: {
        url: snap?.url || refSite,
        host: snap?.host || hostFromUrl(refSite),
        title: snap?.title,
        description: snap?.description,
      },
      draggable: true,
    });
  } else if (refUrl) {
    list.push({
      id: 'reference',
      type: 'reference',
      position: positions.reference || LAYOUT.reference,
      data: {
        name: 'image.png',
        url: refUrl,
      },
      draggable: true,
    });
  }

  const hasSource = Boolean(mdText || refSite || refUrl);
  const specPos = hasSource ? LAYOUT.specAfterSource : LAYOUT.spec;
  const sessionDevice: 'web' | 'app' = session?.device === 'app' ? 'app' : 'web';
  const view = deviceView(sessionDevice);
  const uiPos = uiCanvasPos(specPos);
  const uiStep = view.frameW + DESIGN_CARD_GAP;
  const hasSpec = Boolean(session?.spec);
  const showSpecPlaceholder =
    !hasSpec &&
    (status === 'crafting_spec' || status === 'generating_ui' || Boolean(prompt.trim()) || hasSource);
  if (hasSpec) {
    list.push({
      id: 'spec',
      type: 'spec',
      position: { ...specPos },
      data: { phase: 'ready', spec: session!.spec },
      draggable: true,
    });
  } else if (showSpecPlaceholder) {
    list.push({
      id: 'spec',
      type: 'spec',
      position: { ...specPos },
      data: {
        phase: 'placeholder',
        label: 'Crafting…',
      },
      draggable: true,
    });
  }

  const screens = session?.screens || [];
  const hasAnyHtml = screens.some((s) => Boolean(s.html));
  const showUiPlaceholder =
    !hasAnyHtml &&
    (status === 'generating_ui' ||
      status === 'iterating' ||
      (hasSpec && IN_FLIGHT.has(status)) ||
      // Keep a soft placeholder while ready-but-html-not-yet-hydrated (poll still running).
      (hasSpec && status === 'ready'));

  if (hasAnyHtml) {
    screens.forEach((screen, index) => {
      if (!screen.html) return;
      const nodeId = `ui-${screen.id || index}`;
      const saved = positions[nodeId];
      const fromServer = screen.position;
      const fallbackX = uiPos.x + index * uiStep;
      const serverOk =
        fromServer &&
        typeof fromServer.x === 'number' &&
        fromServer.x >= uiPos.x - 40;
      // Default: fixed row layout. Only keep user-dragged X from positions.
      const position = saved
        ? { x: saved.x, y: DESIGN_ROW_Y }
        : index === 0
          ? { ...uiPos }
          : serverOk
            ? { x: fromServer!.x, y: DESIGN_ROW_Y }
            : { x: fallbackX, y: DESIGN_ROW_Y };
      const pending = extras?.iteratePending;
      const isModifyTarget =
        pending?.mode === 'modify' &&
        (!pending.screenId || pending.screenId === screen.id);
      const uiPhase: UiData['phase'] =
        status === 'generating_ui'
          ? 'drawing'
          : pending?.mode === 'modify' && (status === 'iterating' || drawing)
            ? isModifyTarget
              ? 'drawing'
              : 'ready'
            : drawing || status === 'iterating'
              ? 'drawing'
              : 'ready';
      const isFocusScreen =
        !extras?.pickScreenId || extras.pickScreenId === screen.id;
      const isPickTarget = Boolean(extras?.pickMode) && isFocusScreen;
      const showElementHighlight =
        Boolean(isFocusScreen) &&
        Boolean(extras?.selectedElementPath || extras?.selectedElementLabel);
      const screenName = screen.name || 'Interface';
      const screenId = screen.id || 'main';
      const roundIndex = extras?.selectedRoundIndex ?? activeRound?.index ?? 0;
      const versionedHtml = extras?.roundHtmlByScreen?.[screenId];
      const previewSrc =
        extras?.runId && roundIndex > 0
          ? designScreenVersionPath(extras.runId, screenId, roundIndex)
          : null;
      list.push({
        id: nodeId,
        type: 'ui',
        position,
        selected: extras?.selectedNodeId === nodeId,
        data: {
          phase: uiPhase,
          name: screenName,
          html: versionedHtml ?? screen.html,
          previewSrc,
          screenId,
          device: sessionDevice,
          label:
            uiPhase === 'drawing'
              ? pending?.mode === 'modify'
                ? 'Updating…'
                : 'Generating…'
              : undefined,
          pickMode: isPickTarget,
          selectedElementPath: showElementHighlight ? extras?.selectedElementPath : null,
          selectedElementLabel: showElementHighlight ? extras?.selectedElementLabel : null,
          onElementPicked: extras?.onElementPicked
            ? (payload: { path: string; label: string }) =>
                extras.onElementPicked?.({ ...payload, screenId: screen.id })
            : undefined,
          onTogglePick: extras?.onTogglePick
            ? () =>
                extras.onTogglePick?.({
                  nodeId,
                  screenId: screen.id,
                  name: screenName,
                })
            : undefined,
        },
        draggable: true,
      });
    });
    // New artboard placeholder while adding a screen.
    if (
      extras?.iteratePending?.mode === 'add' &&
      (status === 'iterating' || drawing)
    ) {
      const pendingId = 'ui-pending';
      list.push({
        id: pendingId,
        type: 'ui',
        position:
          positions[pendingId] || {
            x: uiPos.x + screens.length * uiStep,
            y: uiPos.y,
          },
        data: {
          phase: 'placeholder',
          name: 'New screen',
          label: 'Generating…',
          device: sessionDevice,
        },
        draggable: true,
      });
    }
  } else if (showUiPlaceholder) {
    list.push({
      id: 'ui-main',
      type: 'ui',
      position: { ...uiPos },
      data: {
        phase: 'placeholder',
        name: 'Interface',
        label: status === 'ready' ? 'Loading interface…' : 'Sketching…',
        screenId: 'main',
        device: sessionDevice,
      },
      draggable: true,
    });
  }
  return list;
}

function buildCanvasEdges(nodes: Node[]): Edge[] {
  const e: Edge[] = [];
  const hasAgentLog = nodes.some((n) => n.id === 'agentLog');
  const hasRef = nodes.some((n) => n.id === 'reference');
  const hasMd = nodes.some((n) => n.id === 'mdDoc');
  const hasUrl = nodes.some((n) => n.id === 'urlCard');
  const hasSpec = nodes.some((n) => n.id === 'spec');
  const uiNodes = nodes.filter((n) => n.id.startsWith('ui'));
  if (hasAgentLog && hasSpec) {
    e.push({
      id: 'e-agentLog-spec',
      source: 'agentLog',
      target: 'spec',
      markerEnd: { type: MarkerType.ArrowClosed, color: '#d4d4d4' },
      style: { stroke: '#e5e5e5' },
    });
  }
  const sourceId = hasMd ? 'mdDoc' : hasUrl ? 'urlCard' : hasRef ? 'reference' : null;
  if (sourceId && hasSpec) {
    e.push({
      id: `e-${sourceId}-spec`,
      source: sourceId,
      target: 'spec',
      markerEnd: { type: MarkerType.ArrowClosed, color: '#d4d4d4' },
      style: { stroke: '#e5e5e5', strokeDasharray: '4 4' },
    });
  }
  for (const ui of uiNodes) {
    if (hasSpec) {
      e.push({
        id: `e-spec-${ui.id}`,
        source: 'spec',
        target: ui.id,
        markerEnd: { type: MarkerType.ArrowClosed, color: '#d4d4d4' },
        style: { stroke: '#e5e5e5' },
      });
    }
  }
  return e;
}

function DesignCanvasInner({
  runId,
  modelLabel,
  onOpenModels,
  onSendToCoding,
  onSessionTitle,
  onBusyChange,
}: Omit<DesignWorkspaceProps, 'workspaceReady'>) {
  const { t } = useLanguage();
  const [session, setSession] = useState<DesignSession | null>(null);
  const [prompt, setPrompt] = useState('');
  const [referenceImage, setReferenceImage] = useState<{ name: string; dataUrl: string } | null>(null);
  const [referenceMd, setReferenceMd] = useState<{ name: string; text: string } | null>(null);
  const [referenceUrl, setReferenceUrl] = useState<string | null>(null);
  const [urlDraft, setUrlDraft] = useState('');
  const [showUrlField, setShowUrlField] = useState(false);
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [designSystem, setDesignSystem] = useState<DesignSystemId>('clutch');
  const [designSystemMenuOpen, setDesignSystemMenuOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const mdInputRef = useRef<HTMLInputElement | null>(null);
  const [device, setDevice] = useState<'web' | 'app'>('web');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [iterateText, setIterateText] = useState('');
  const [iteratePending, setIteratePending] = useState<IteratePending | null>(null);
  const [focusNodeIds, setFocusNodeIds] = useState<string[] | undefined>(undefined);
  const [showCodeTray, setShowCodeTray] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [welcomeMode, setWelcomeMode] = useState(true);
  const [canvasSelection, setCanvasSelection] = useState<CanvasSelection | null>(null);
  const [elementSelection, setElementSelection] = useState<ElementSelection | null>(null);
  const [pickMode, setPickMode] = useState(false);
  const [selectedRoundIndex, setSelectedRoundIndex] = useState(0);
  const [roundHtmlByScreen, setRoundHtmlByScreen] = useState<Record<string, string | undefined>>({});
  const roundPinnedRef = useRef(false);
  const selectedRoundRef = useRef(0);
  const clipboardRef = useRef<CanvasSelection | null>(null);
  const canvasSelectionRef = useRef<CanvasSelection | null>(null);
  const pickModeRef = useRef(false);
  const iteratePendingRef = useRef<IteratePending | null>(null);
  canvasSelectionRef.current = canvasSelection;
  pickModeRef.current = pickMode;
  iteratePendingRef.current = iteratePending;
  const [nodes, setNodes] = useNodesState<Node>([]);
  const [edges, setEdges] = useEdgesState<Edge>([]);
  const [layoutKey, setLayoutKey] = useState('');
  const pollRef = useRef<number | null>(null);
  const hadSpecRef = useRef(false);
  const hadScreenRef = useRef(false);
  const positionsRef = useRef<Record<string, { x: number; y: number }>>({});
  const userDraggedRef = useRef(false);
  const drawingRef = useRef(false);
  const promptRef = useRef('');
  const designLogKeysRef = useRef<Set<string>>(new Set());

  drawingRef.current = drawing;
  promptRef.current = prompt;
  selectedRoundRef.current = selectedRoundIndex;
  const lastBusyRef = useRef<boolean | null>(null);
  const currentRunIdRef = useRef(runId);
  currentRunIdRef.current = runId;


  useEffect(() => {
    const waitingHtml =
      session?.status === 'ready' && !session.screens?.some((s) => Boolean(s.html));
    const generating =
      busy || Boolean(session && IN_FLIGHT.has(session.status)) || Boolean(waitingHtml);
    if (lastBusyRef.current === generating) return;
    lastBusyRef.current = generating;
    onBusyChange?.(generating, { device });
  }, [busy, session?.status, session?.screens, onBusyChange, device]);

  const stopPoll = useCallback(() => {
    if (pollRef.current != null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const publishRoundLogs = useCallback((round: DesignRound | null) => {
    clutchStore.clearTerminalLogs();
    if (!round) return;
    if (round.reasoning_content?.trim()) {
      clutchStore.appendTerminalLog(
        `[DESIGN:REASONING] ${round.reasoning_content.trim().replace(/\n/g, ' ↵ ')}`,
      );
    }
    if (round.user_prompt.trim()) {
      clutchStore.appendTerminalLog(`[USER] ${round.user_prompt}`);
    }
    for (const entry of round.entries) {
      if (!entry.text?.trim()) continue;
      const statusBit = entry.status ? ` · ${entry.status}` : '';
      clutchStore.appendTerminalLog(`[DESIGN] ${entry.text}${statusBit}`);
    }
  }, []);

  const syncDesignTerminalLogs = useCallback(
    (next: DesignSession, roundIndex: number) => {
      const rounds = parseDesignRounds(next.process_log, next.rounds, next.round_history);
      const round = rounds.find((r) => r.index === roundIndex) ?? rounds[rounds.length - 1] ?? null;
      publishRoundLogs(round);

      const stamp = () => {
        const d = new Date();
        const pad = (n: number) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
      };
      const htmlCount = (next.screens || []).filter((s) => Boolean(s.html)).length;
      const statusKey = `status:${next.status}:screens=${next.screens?.length || 0}:html=${htmlCount}:round=${roundIndex}`;
      if (!designLogKeysRef.current.has(statusKey)) {
        designLogKeysRef.current.add(statusKey);
        clutchStore.appendTerminalLog(
          `[${stamp()}] [DESIGN] status=${next.status} round=${roundIndex} screens=${next.screens?.length || 0} html=${htmlCount}${
            next.ui_preview_url ? ` preview=${next.ui_preview_url}` : ''
          }`,
        );
      }
    },
    [publishRoundLogs],
  );

  const syncNodesFromSession = useCallback(
    (
      next: DesignSession | null,
      nextPrompt: string,
      nextDrawing: boolean,
      extras?: {
        referenceImageUrl?: string | null;
        referenceMd?: { name: string; text: string } | null;
        referenceUrl?: string | null;
      },
    ) => {
      const selectedId = canvasSelectionRef.current?.nodeId ?? null;
      const built = buildCanvasNodes(
        next,
        nextPrompt,
        nextDrawing,
        userDraggedRef.current ? positionsRef.current : {},
        {
          referenceImageUrl:
            extras?.referenceImageUrl ?? next?.reference_image_url ?? referenceImage?.dataUrl,
          referenceMd: extras?.referenceMd ?? (next?.reference_md_text
            ? { name: next.reference_md_name || 'DESIGN.md', text: next.reference_md_text }
            : referenceMd),
          referenceUrl: extras?.referenceUrl ?? next?.reference_url ?? referenceUrl,
          pickMode,
          selectedElementLabel: elementSelection?.label ?? null,
          selectedElementPath: elementSelection?.path ?? null,
          pickScreenId: canvasSelectionRef.current?.screenId || elementSelection?.screenId || null,
          selectedNodeId: selectedId,
          iteratePending: iteratePendingRef.current,
          selectedRoundIndex,
          roundHtmlByScreen,
          runId,
          onTogglePick: ({ nodeId, screenId, name }) => {
            const already =
              canvasSelectionRef.current?.nodeId === nodeId && pickModeRef.current;
            setCanvasSelection({
              nodeId,
              kind: 'ui',
              label: name,
              screenId,
            });
            setNodes((nds) => nds.map((n) => ({ ...n, selected: n.id === nodeId })));
            if (already) {
              setPickMode(false);
            } else {
              setPickMode(true);
              setElementSelection(null);
            }
          },
        },
      );
      for (const node of built) {
        // Default layout is authoritative until the user drags a card.
        if (userDraggedRef.current && positionsRef.current[node.id]) {
          const saved = positionsRef.current[node.id];
          node.position = {
            x: saved.x,
            y: node.id === 'agentLog' || node.id === 'spec' || node.id.startsWith('ui')
              ? DESIGN_ROW_Y
              : saved.y,
          };
        } else {
          positionsRef.current[node.id] = { ...node.position };
        }
        node.selected = node.id === selectedId;
      }
      setNodes(built);
      setEdges(buildCanvasEdges(built));
      const key = built.map((n) => n.id).join('-');
      if (key && !userDraggedRef.current) {
        setLayoutKey(`${key}-${next?.status || ''}`);
      }
    },
    [
      setNodes,
      setEdges,
      t,
      referenceImage?.dataUrl,
      referenceMd,
      referenceUrl,
      pickMode,
      elementSelection?.label,
      elementSelection?.screenId,
      elementSelection?.path,
      iteratePending,
      selectedRoundIndex,
      roundHtmlByScreen,
      runId,
    ],
  );

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      setNodes((nds) => {
        const next = applyNodeChanges(changes, nds);
        for (const change of changes) {
          if (change.type === 'position' && change.position && change.id) {
            positionsRef.current[change.id] = { ...change.position };
            if (change.dragging === false) {
              userDraggedRef.current = true;
            }
          }
        }
        return next;
      });
    },
    [setNodes],
  );

  const applySession = useCallback(
    (next: DesignSession) => {
      if (next.run_id !== currentRunIdRef.current && next.id !== currentRunIdRef.current) {
        return;
      }
      const rounds = parseDesignRounds(next.process_log, next.rounds, next.round_history);
      const latestRoundIndex = rounds[rounds.length - 1]?.index ?? 0;
      const effectiveRoundIndex =
        !roundPinnedRef.current || !rounds.some((r) => r.index === selectedRoundRef.current)
          ? latestRoundIndex
          : selectedRoundRef.current;
      setSession(next);
      setSelectedRoundIndex(effectiveRoundIndex);
      setPreviewUrl(next.preview_url ?? null);
      if (next.device === 'app' || next.device === 'web') {
        setDevice(next.device);
      }
      if (next.prompt) setPrompt(next.prompt);
      if (next.reference_image_url) {
        setReferenceImage((prev) => prev ?? { name: 'image.png', dataUrl: next.reference_image_url! });
      }
      if (next.reference_md_text) {
        setReferenceMd((prev) =>
          prev ?? {
            name: next.reference_md_name || 'DESIGN.md',
            text: next.reference_md_text!,
          },
        );
      }
      if (next.reference_url) {
        setReferenceUrl((prev) => prev ?? next.reference_url!);
      }
      const hasSource = Boolean(
        next.reference_image_url || next.reference_md_text || next.reference_url,
      );
      const hasHtml = Boolean(next.screens?.some((s) => Boolean(s.html)));
      const hasCanvas = Boolean(
        next.spec || next.screens?.length || IN_FLIGHT.has(next.status) || hasSource,
      );
      setWelcomeMode(isWelcomeSession(next) || (!hasCanvas && !next.prompt?.trim() && !hasSource));
      if (next.error) setError(next.error);
      if (next.spec && !hadSpecRef.current) {
        hadSpecRef.current = true;
      }
      let nextDrawing = drawingRef.current;
      if (hasHtml && !hadScreenRef.current) {
        hadScreenRef.current = true;
        nextDrawing = true;
        setDrawing(true);
        window.setTimeout(() => setDrawing(false), 1450);
      }
      // Sidebar spinner must track real UI hydrate, not just status=ready.
      if (next.status === 'error') {
        setBusy(false);
      } else if (next.status === 'ready' && hasHtml) {
        setBusy(false);
      } else if (IN_FLIGHT.has(next.status) || (next.status === 'ready' && !hasHtml)) {
        setBusy(true);
      }
      syncDesignTerminalLogs(next, effectiveRoundIndex);
      if (isWelcomeSession(next) && !hasSource) {
        setBusy(false);
        setNodes([]);
        setEdges([]);
        return;
      }
      syncNodesFromSession(next, next.prompt || promptRef.current, nextDrawing, {
        referenceImageUrl: next.reference_image_url,
        referenceMd: next.reference_md_text
          ? { name: next.reference_md_name || 'DESIGN.md', text: next.reference_md_text }
          : null,
        referenceUrl: next.reference_url,
      });
    },
    [syncNodesFromSession, setNodes, setEdges, syncDesignTerminalLogs],
  );

  const enrichSessionHtml = useCallback(async (next: DesignSession): Promise<DesignSession> => {
    const screens = next.screens || [];
    if (!screens.some((s) => s.id && !s.html)) return next;
    const filled = await Promise.all(
      screens.map(async (screen) => {
        if (screen.html || !screen.id) return screen;
        try {
          const html = await getDesignScreenHtml(runId, screen.id);
          if (!html?.trim()) return screen;
          return { ...screen, html };
        } catch {
          return screen;
        }
      }),
    );
    return { ...next, screens: filled };
  }, [runId]);

  const startPoll = useCallback(() => {
    stopPoll();
    let ticks = 0;
    pollRef.current = window.setInterval(() => {
      ticks += 1;
      void getDesignSession(runId)
        .then(async (raw) => {
          const next = await enrichSessionHtml(raw);
          applySession(next);
          const hasHtml = Boolean(next.screens?.some((s) => Boolean(s.html)));
          if (next.status === 'error') {
            stopPoll();
            return;
          }
          if (next.status === 'ready' && hasHtml) {
            stopPoll();
            return;
          }
          // ready without html: keep polling briefly (folder rename / write race).
          if (next.status === 'ready' && !hasHtml && ticks >= 25) {
            stopPoll();
            setBusy(false);
            setError((prev) => prev || 'Interface HTML not available yet — try reopening the session.');
            clutchStore.appendTerminalLog(
              '[DESIGN] ready but screen HTML missing after poll timeout',
            );
          }
          if (ticks >= 120) {
            stopPoll();
            setBusy(false);
          }
        })
        .catch((err) => {
          clutchStore.appendTerminalLog(
            `[DESIGN] poll error: ${err instanceof Error ? err.message : String(err)}`,
          );
        });
    }, 900);
  }, [runId, applySession, stopPoll, enrichSessionHtml]);

  const hydrate = useCallback(async () => {
    if (!runId) return;
    try {
      designLogKeysRef.current = new Set();
      await ensureDesignSession({ run_id: runId, title: t('New Design') });
      const raw = await getDesignSession(runId);
      const next = await enrichSessionHtml(raw);
      hadSpecRef.current = Boolean(next.spec);
      hadScreenRef.current = Boolean(next.screens?.[0]?.html);
      userDraggedRef.current = false;
      positionsRef.current = {};
      applySession(next);
      const waitingHtml =
        next.status === 'ready' && !next.screens?.some((s) => Boolean(s.html));
      if (IN_FLIGHT.has(next.status) || waitingHtml) {
        setBusy(true);
        setWelcomeMode(false);
        startPoll();
      } else if (isWelcomeSession(next)) {
        setBusy(false);
        setWelcomeMode(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [runId, t, applySession, startPoll, enrichSessionHtml]);

  useEffect(() => {
    // Reset surface immediately when switching Design sessions.
    setWelcomeMode(true);
    setSession(null);
    setPrompt('');
    setReferenceImage(null);
    setReferenceMd(null);
    setReferenceUrl(null);
    setUrlDraft('');
    setShowUrlField(false);
    setAttachMenuOpen(false);
    setCanvasSelection(null);
    setElementSelection(null);
    setPickMode(false);
    setNodes([]);
    setEdges([]);
    setBusy(false);
    setError(null);
    setDrawing(false);
    setIterateText('');
    setShowCodeTray(false);
    setPreviewUrl(null);
    setSelectedRoundIndex(0);
    setRoundHtmlByScreen({});
    roundPinnedRef.current = false;
    selectedRoundRef.current = 0;
    hadSpecRef.current = false;
    hadScreenRef.current = false;
    userDraggedRef.current = false;
    positionsRef.current = {};
    lastBusyRef.current = null;
    stopPoll();
    void hydrate();
    return () => stopPoll();
  }, [runId]); // eslint-disable-line react-hooks/exhaustive-deps -- remount surface per session

  useEffect(() => {
    if (welcomeMode || !session) return;
    syncNodesFromSession(session, prompt, drawing);
  }, [drawing]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (welcomeMode || !session) return;
    syncNodesFromSession(session, prompt, drawing, {
      referenceImageUrl: referenceImage?.dataUrl,
      referenceMd,
      referenceUrl,
    });
  }, [referenceImage?.dataUrl, referenceMd, referenceUrl, pickMode, elementSelection?.label, elementSelection?.path]); // eslint-disable-line react-hooks/exhaustive-deps

  const designRounds = parseDesignRounds(session?.process_log, session?.rounds, session?.round_history);

  const handleRoundSelect = useCallback(
    (index: number) => {
      roundPinnedRef.current = true;
      setSelectedRoundIndex(index);
      if (session) {
        const rounds = parseDesignRounds(session.process_log, session.rounds, session.round_history);
        const round = rounds.find((r) => r.index === index) ?? null;
        publishRoundLogs(round);
      }
    },
    [session, publishRoundLogs],
  );

  useEffect(() => {
    if (welcomeMode || !session) return;
    const screens = session.screens || [];
    if (!screens.length) return;
    let cancelled = false;

    void (async () => {
      const nextMap: Record<string, string | undefined> = {};
      await Promise.all(
        screens.map(async (screen) => {
          const screenId = screen.id || 'main';
          const versionedId = versionedDesignScreenId(screenId, selectedRoundIndex);
          try {
            const html = await getDesignScreenHtml(runId, versionedId);
            if (html?.trim()) {
              nextMap[screenId] = html;
              return;
            }
          } catch {
            // Versioned screen not persisted yet — fall back below.
          }
          if (screen.html?.trim()) {
            nextMap[screenId] = screen.html;
            return;
          }
          try {
            const html = await getDesignScreenHtml(runId, screenId);
            if (html?.trim()) nextMap[screenId] = html;
          } catch {
            nextMap[screenId] = screen.html;
          }
        }),
      );
      if (!cancelled) setRoundHtmlByScreen(nextMap);
    })();

    return () => {
      cancelled = true;
    };
  }, [welcomeMode, session, selectedRoundIndex, runId]);

  const withBusy = async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
      return undefined;
    }
  };

  const addImageFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      setReferenceImage({ name: file.name || 'image.png', dataUrl: reader.result as string });
      setReferenceMd(null);
      setReferenceUrl(null);
      setShowUrlField(false);
    };
    reader.readAsDataURL(file);
  }, []);

  const addMdFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const name = file.name || 'DESIGN.md';
      const text = String(reader.result || '');
      setReferenceMd({ name, text });
      setReferenceImage(null);
      setReferenceUrl(null);
      setShowUrlField(false);
      setPrompt((prev) => {
        const trimmed = prev.trim();
        if (!trimmed || /使用 the file \[/.test(trimmed) || /Use the file \[/.test(trimmed)) {
          return autoPromptForMd(name);
        }
        return prev;
      });
    };
    reader.readAsText(file);
  }, []);

  const commitUrl = useCallback((raw: string) => {
    const value = raw.trim();
    if (!value) return;
    const normalized = /^https?:\/\//i.test(value) ? value : `https://${value}`;
    setReferenceUrl(normalized);
    setReferenceImage(null);
    setReferenceMd(null);
    setShowUrlField(false);
    setUrlDraft('');
    setPrompt((prev) => (prev.trim() ? prev : autoPromptForUrl()));
  }, []);

  const handlePasteImage = useCallback(
    (e: React.ClipboardEvent) => {
      const text = e.clipboardData.getData('text/plain')?.trim();
      if (text && /^https?:\/\/\S+$/i.test(text)) {
        e.preventDefault();
        commitUrl(text);
        return;
      }
      const { files } = e.clipboardData;
      if (!files || files.length === 0) return;
      for (const file of Array.from(files)) {
        if (file.type.startsWith('image/')) {
          e.preventDefault();
          addImageFile(file);
          return;
        }
      }
    },
    [addImageFile, commitUrl],
  );

  const handleGenerate = async () => {
    const hasRef = Boolean(referenceImage || referenceMd || referenceUrl);
    const text =
      prompt.trim() ||
      (referenceMd
        ? autoPromptForMd(referenceMd.name)
        : referenceUrl
          ? autoPromptForUrl()
          : referenceImage
            ? t('Match this reference UI')
            : '');
    if (!text && !hasRef) return;
    setWelcomeMode(false);
    setBusy(true);
    setError(null);
    setAttachMenuOpen(false);
    setDesignSystemMenuOpen(false);
    hadSpecRef.current = false;
    hadScreenRef.current = false;
    userDraggedRef.current = false;
    positionsRef.current = {};
    designLogKeysRef.current = new Set();
    roundPinnedRef.current = false;
    clutchStore.appendTerminalLog(
      `[DESIGN] generate requested device=${device} prompt=${JSON.stringify((text || '').slice(0, 80))}`,
    );
    onSessionTitle?.(text.slice(0, 48) || t('New Design'), { device });
    const next = await withBusy(() =>
      generateDesignSession(runId, {
        prompt: text || '生成设计系统与界面',
        device,
        reference_image: referenceImage?.dataUrl ?? null,
        reference_md: referenceMd?.text ?? null,
        reference_md_name: referenceMd?.name ?? null,
        reference_url: referenceUrl,
        design_system: hasRef ? undefined : designSystem,
      }),
    );
    if (next) {
      applySession(next);
      startPoll();
    } else {
      setBusy(false);
    }
  };

  const handleIterate = async () => {
    if (!iterateText.trim() || !session) return;
    const instruction = iterateText.trim();
    const mode = inferIterateModeClient(instruction, canvasSelection?.kind ?? 'ui');
    const targetId =
      canvasSelection?.screenId ?? session.screens?.[0]?.id ?? null;
    const now = new Date().toISOString();
    const pending: IteratePending = { mode, screenId: targetId };
    setIteratePending(pending);
    iteratePendingRef.current = pending;
    roundPinnedRef.current = false;
    setDrawing(true);
    setBusy(true);
    setError(null);
    // Focus spec / target screen; execution status lives in Agent Log.
    userDraggedRef.current = false;
    const iterateFocusId =
      mode === 'modify' && targetId
        ? `ui-${targetId}`
        : session.spec
          ? 'spec'
          : session.screens?.[0]?.id
            ? `ui-${session.screens[0].id}`
            : 'spec';
    setFocusNodeIds([iterateFocusId]);
    setCanvasSelection({
      nodeId: iterateFocusId,
      kind: iterateFocusId.startsWith('ui') ? 'ui' : 'spec',
      label:
        iterateFocusId.startsWith('ui')
          ? session.screens?.find((s) => `ui-${s.id}` === iterateFocusId)?.name || 'Interface'
          : String(session.spec?.name || 'Design system'),
      screenId: iterateFocusId.startsWith('ui')
        ? iterateFocusId.replace(/^ui-/, '')
        : undefined,
    });
    const optimistic: DesignSession = {
      ...session,
      status: 'iterating',
      process_log: [
        ...(session.process_log || []),
        { role: 'user', text: instruction, at: now },
        {
          role: 'assistant',
          text:
            mode === 'add'
              ? 'Creating a new version…'
              : 'Thinking… applying your changes to the selected design.',
          status: 'iterating',
          at: now,
        },
      ],
    };
    setSession(optimistic);
    syncNodesFromSession(optimistic, optimistic.prompt || prompt, true);
    setLayoutKey(`iterate-start-${Date.now()}`);

    const next = await withBusy(() =>
      iterateDesignSession(runId, instruction, {
        target_kind: canvasSelection?.kind ?? 'ui',
        target_id: targetId,
        element_path: elementSelection?.path ?? null,
        element_label: elementSelection?.label ?? null,
        mode,
      }),
    );
    if (next) {
      const action = next.last_iterate_action;
      const focusScreen =
        next.last_iterate_screen_id ||
        targetId ||
        next.screens?.[next.screens.length - 1]?.id;
      setIterateText('');
      setPickMode(false);
      setIteratePending(null);
      iteratePendingRef.current = null;
      applySession(next);
      setDrawing(true);
      window.setTimeout(() => setDrawing(false), 1450);
      setBusy(false);
      userDraggedRef.current = false;
      const focusId = focusScreen ? `ui-${focusScreen}` : 'spec';
      setFocusNodeIds([focusId]);
      setLayoutKey(`iterate-done-${Date.now()}-${action || mode}`);
      setCanvasSelection({
        nodeId: focusId,
        kind: 'ui',
        label: next.screens?.find((s) => s.id === focusScreen)?.name || 'Interface',
        screenId: focusScreen || undefined,
      });
    } else {
      setIteratePending(null);
      iteratePendingRef.current = null;
      setDrawing(false);
      setBusy(false);
      setFocusNodeIds(undefined);
    }
  };

  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes }: { nodes: Node[] }) => {
      const node = selectedNodes[0];
      if (!node) return;
      const kind = selectionKindFromNodeId(node.id);
      const data = node.data as UiData;
      setCanvasSelection({
        nodeId: node.id,
        kind,
        label: selectionLabel(kind, node, session),
        screenId: data.screenId || (kind === 'ui' ? session?.screens?.[0]?.id : undefined),
      });
      if (kind !== 'ui') {
        setPickMode(false);
        setElementSelection(null);
      }
    },
    [session],
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const kind = selectionKindFromNodeId(node.id);
      const data = node.data as UiData;
      setCanvasSelection({
        nodeId: node.id,
        kind,
        label: selectionLabel(kind, node, session),
        screenId: data.screenId || (kind === 'ui' ? session?.screens?.[0]?.id : undefined),
      });
      if (kind !== 'ui') {
        setPickMode(false);
        setElementSelection(null);
      }
    },
    [session],
  );

  const onPaneClick = useCallback(() => {
    setCanvasSelection(null);
    setElementSelection(null);
    setPickMode(false);
    setNodes((nds) => nds.map((n) => ({ ...n, selected: false })));
  }, [setNodes]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const data = event.data as { source?: string; path?: string; label?: string };
      if (data?.source !== 'clutch-design-pick' || !data.path) return;
      setElementSelection({
        path: data.path,
        label: data.label || data.path,
        screenId: canvasSelection?.screenId || session?.screens?.[0]?.id,
      });
      setPickMode(false);
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [canvasSelection?.screenId, session?.screens]);

  useEffect(() => {
    if (welcomeMode) return;
    const onKey = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;
      if (!meta) return;
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
      if (e.key === 'c' && canvasSelection) {
        e.preventDefault();
        clipboardRef.current = canvasSelection;
      }
      if (e.key === 'v' && clipboardRef.current) {
        e.preventDefault();
        const clip = clipboardRef.current;
        if (clip.kind === 'ui') {
          setIterateText((prev) => prev || t('Create another screen based on the selection'));
          setCanvasSelection(clip);
          void (async () => {
            setDrawing(true);
            setBusy(true);
            const next = await withBusy(() =>
              iterateDesignSession(runId, t('Create another screen based on the selection'), {
                target_kind: 'ui',
                target_id: clip.screenId ?? null,
                mode: 'add',
              }),
            );
            if (next) {
              applySession(next);
              setBusy(false);
              setDrawing(false);
            } else {
              setBusy(false);
              setDrawing(false);
            }
          })();
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [welcomeMode, canvasSelection, runId, t, applySession]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      {welcomeMode ? (
        <div className="relative z-10 flex h-full flex-col items-center justify-center px-6">
          <h1 className="mb-8 text-2xl font-bold tracking-tight text-neutral-900">
            {t('Welcome to Design')}
          </h1>
          <div
            className="w-full max-w-2xl rounded-[28px] border border-neutral-200/80 bg-white/90 p-4 shadow-lg backdrop-blur-md"
            onPaste={handlePasteImage}
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const files = Array.from(e.dataTransfer.files);
              const md = files.find((f) => /\.(md|markdown|txt)$/i.test(f.name));
              if (md) {
                addMdFile(md);
                return;
              }
              const img = files.find((f) => f.type.startsWith('image/'));
              if (img) addImageFile(img);
            }}
          >
            {(referenceImage || referenceMd || referenceUrl) && (
              <div className="mb-2 flex flex-wrap items-center gap-2 px-2">
                {referenceImage ? (
                  <span className="inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 py-1 pl-1.5 pr-2 text-[11px] font-medium text-neutral-700">
                    <img
                      src={referenceImage.dataUrl}
                      alt=""
                      className="h-5 w-5 rounded-full object-cover"
                    />
                    <span className="truncate">{referenceImage.name}</span>
                    <button
                      type="button"
                      className="ml-0.5 rounded-full p-0.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700"
                      onClick={() => setReferenceImage(null)}
                      aria-label={t('Remove reference image')}
                    >
                      <X size={12} />
                    </button>
                  </span>
                ) : null}
                {referenceMd ? (
                  <span className="inline-flex max-w-[260px] items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 py-1 pl-2 pr-2 text-[11px] font-medium text-neutral-700">
                    <FileText size={13} className="shrink-0 text-neutral-500" />
                    <span className="truncate">{referenceMd.name}</span>
                    <button
                      type="button"
                      className="ml-0.5 rounded-full p-0.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700"
                      onClick={() => setReferenceMd(null)}
                      aria-label={t('Remove file')}
                    >
                      <X size={12} />
                    </button>
                  </span>
                ) : null}
                {referenceUrl ? (
                  <span className="inline-flex max-w-[260px] items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 py-1 pl-2 pr-2 text-[11px] font-medium text-neutral-700">
                    <Globe size={13} className="shrink-0 text-sky-600" />
                    <span className="truncate">{hostFromUrl(referenceUrl)}</span>
                    <button
                      type="button"
                      className="ml-0.5 rounded-full p-0.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700"
                      onClick={() => setReferenceUrl(null)}
                      aria-label={t('Remove URL')}
                    >
                      <X size={12} />
                    </button>
                  </span>
                ) : null}
              </div>
            )}
            {showUrlField ? (
              <div className="mb-2 flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2">
                <Globe size={14} className="shrink-0 text-neutral-400" />
                <input
                  autoFocus
                  className="min-w-0 flex-1 bg-transparent text-[13px] text-neutral-800 placeholder:text-neutral-400 focus:outline-none"
                  placeholder={t('Paste URL…')}
                  value={urlDraft}
                  onChange={(e) => setUrlDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      commitUrl(urlDraft);
                    }
                    if (e.key === 'Escape') {
                      setShowUrlField(false);
                      setUrlDraft('');
                    }
                  }}
                />
                <button
                  type="button"
                  className="rounded-full bg-neutral-900 px-2.5 py-1 text-[11px] font-semibold text-white disabled:opacity-40"
                  disabled={!urlDraft.trim()}
                  onClick={() => commitUrl(urlDraft)}
                >
                  {t('Add URL')}
                </button>
              </div>
            ) : null}
            <textarea
              className="min-h-[88px] w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-relaxed text-neutral-800 placeholder:text-neutral-400 focus:outline-none"
              placeholder={
                referenceMd || referenceUrl || referenceImage
                  ? t('Describe changes, or send to match the reference')
                  : t('What do you want to design?')
              }
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onPaste={handlePasteImage}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void handleGenerate();
                }
              }}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) addImageFile(file);
                e.target.value = '';
              }}
            />
            <input
              ref={mdInputRef}
              type="file"
              accept=".md,.markdown,.txt,text/markdown,text/plain"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) addMdFile(file);
                e.target.value = '';
              }}
            />
            <div className="mt-2 flex items-center justify-between gap-2">
              <div className="relative flex items-center gap-1.5">
                <button
                  type="button"
                  className="rounded-full p-2 text-neutral-500 hover:bg-neutral-100"
                  onClick={() => {
                    setDesignSystemMenuOpen(false);
                    setAttachMenuOpen((v) => !v);
                  }}
                  title={t('Add attachment')}
                  aria-label={t('Add attachment')}
                >
                  <Plus size={16} />
                </button>
                {attachMenuOpen ? (
                  <div className="absolute bottom-full left-0 z-30 mb-2 w-48 overflow-hidden rounded-xl border border-neutral-200 bg-white py-1 shadow-lg">
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-neutral-700 hover:bg-neutral-50"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        setShowUrlField(true);
                      }}
                    >
                      <Globe size={14} /> {t('Website URL')}
                    </button>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-neutral-700 hover:bg-neutral-50"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        mdInputRef.current?.click();
                      }}
                    >
                      <FileText size={14} /> {t('Upload file')}
                    </button>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-neutral-700 hover:bg-neutral-50"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        fileInputRef.current?.click();
                      }}
                    >
                      <ImagePlus size={14} /> {t('Upload image')}
                    </button>
                  </div>
                ) : null}
                <button
                  type="button"
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                    device === 'app' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-100'
                  }`}
                  onClick={() => setDevice('app')}
                >
                  <Smartphone size={13} />
                  {t('App')}
                </button>
                <button
                  type="button"
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                    device === 'web' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-100'
                  }`}
                  onClick={() => setDevice('web')}
                >
                  <Monitor size={13} />
                  {t('Web')}
                </button>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="relative">
                  <button
                    type="button"
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold transition-colors ${
                      referenceImage || referenceMd || referenceUrl
                        ? 'cursor-not-allowed text-neutral-300'
                        : designSystemMenuOpen
                          ? 'bg-neutral-100 text-neutral-800'
                          : 'text-neutral-600 hover:bg-neutral-100'
                    }`}
                    disabled={Boolean(referenceImage || referenceMd || referenceUrl)}
                    title={
                      referenceImage || referenceMd || referenceUrl
                        ? t('Reference attachment overrides the design system preset.')
                        : t('Design system')
                    }
                    aria-label={t('Design system')}
                    onClick={() => {
                      if (referenceImage || referenceMd || referenceUrl) return;
                      setAttachMenuOpen(false);
                      setDesignSystemMenuOpen((v) => !v);
                    }}
                  >
                    <Palette size={14} />
                    <span>
                      {t(
                        DESIGN_SYSTEM_PRESETS.find((p) => p.id === designSystem)?.labelKey
                          ?? 'Clutch',
                      )}
                    </span>
                    <ChevronDown size={12} className="opacity-60" />
                  </button>
                  {designSystemMenuOpen && !(referenceImage || referenceMd || referenceUrl) ? (
                    <div className="absolute bottom-full right-0 z-30 mb-2 w-72 overflow-hidden rounded-xl border border-neutral-200 bg-white py-1 shadow-lg">
                      <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
                        {t('Design system')}
                      </p>
                      {DESIGN_SYSTEM_PRESETS.map((preset) => {
                        const active = designSystem === preset.id;
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            className={`flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-neutral-50 ${
                              active ? 'bg-neutral-50' : ''
                            }`}
                            onClick={() => {
                              setDesignSystem(preset.id);
                              setDesignSystemMenuOpen(false);
                            }}
                          >
                            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-neutral-200 bg-gradient-to-br from-neutral-800 via-neutral-500 to-neutral-200" />
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center justify-between gap-2 text-[12px] font-semibold text-neutral-900">
                                {t(preset.labelKey)}
                                {active ? <Check size={14} className="text-sky-600" /> : null}
                              </span>
                              <span className="mt-0.5 block text-[11px] leading-snug text-neutral-500">
                                {t(preset.descriptionKey)}
                              </span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={onOpenModels}
                  className="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-[11px] font-semibold text-neutral-700"
                >
                  <Sparkles size={12} />
                  {modelLabel || 'Model'}
                </button>
                <button type="button" className="rounded-full p-2 text-neutral-400" disabled>
                  <Mic size={15} />
                </button>
                <button
                  type="button"
                  disabled={busy || (!prompt.trim() && !referenceImage && !referenceMd && !referenceUrl)}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-neutral-900 text-white disabled:opacity-40"
                  onClick={() => void handleGenerate()}
                  aria-label="Send"
                >
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} />}
                </button>
              </div>
            </div>
          </div>
          <p className="mt-3 text-center text-[12px] text-neutral-400">
            {t('Attach Design.md, a website URL, or a reference image')}
          </p>
          {error ? (
            <p className="mt-4 max-w-lg text-center text-[12px] text-rose-600">{error}</p>
          ) : null}
        </div>
      ) : (
        <>
          <div className="absolute inset-0 z-0">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onSelectionChange={onSelectionChange}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              nodesDraggable
              nodesConnectable={false}
              elementsSelectable
              panOnDrag={[1, 2]}
              selectionOnDrag={false}
              selectNodesOnDrag={false}
              defaultViewport={{ x: 24, y: 24, zoom: 0.85 }}
              minZoom={0.35}
              maxZoom={1.25}
              panOnScroll
              proOptions={{ hideAttribution: true }}
              className="!bg-transparent"
            >
              <Background gap={18} size={1} color="#d4d4d8" />
              <Controls
                position="bottom-left"
                className="!mb-[4.5rem] !ml-3 !overflow-visible !rounded-xl !border !border-neutral-200 !bg-white/95 !shadow-sm"
              />
              <FitViewOnNodes layoutKey={layoutKey} focusIds={focusNodeIds} />
            </ReactFlow>
          </div>

          <div
            className="pointer-events-none absolute inset-x-0 z-20 flex justify-center px-4"
            style={{ bottom: APP_INPUT_DOCK_BOTTOM_PX + 72 }}
          >
            <DesignRoundSelector
              rounds={designRounds}
              selectedRoundIndex={selectedRoundIndex}
              onSelect={handleRoundSelect}
            />
          </div>

          <div
            className="pointer-events-none absolute inset-x-0 z-20 flex justify-center px-4"
            style={{ bottom: APP_INPUT_DOCK_BOTTOM_PX }}
          >
            <div
              className="pointer-events-auto flex w-full max-w-2xl flex-col gap-1.5 rounded-2xl border border-outline-variant/30 bg-white/90 px-3 py-2 shadow-md backdrop-blur-md"
              onPaste={handlePasteImage}
            >
              {(canvasSelection || elementSelection) && (
                <div className="flex flex-wrap items-center gap-1.5 px-0.5">
                  {canvasSelection ? (
                    <span className="inline-flex max-w-[240px] items-center gap-1 rounded-full border border-outline-variant/40 bg-surface-container-low py-0.5 pl-2 pr-1 text-[11px] font-medium text-on-surface">
                      <span className="shrink-0 text-on-surface-variant">
                        {canvasSelection.kind === 'ui' ? t('Artboard') : t('Selected')}
                      </span>
                      <span className="truncate">{canvasSelection.label}</span>
                      <button
                        type="button"
                        className="rounded-full p-0.5 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                        onClick={() => {
                          setCanvasSelection(null);
                          setElementSelection(null);
                          setPickMode(false);
                          setNodes((nds) => nds.map((n) => ({ ...n, selected: false })));
                        }}
                        aria-label={t('Clear selection')}
                      >
                        <X size={11} />
                      </button>
                    </span>
                  ) : null}
                  {elementSelection ? (
                    <span className="inline-flex max-w-[220px] items-center gap-1 rounded-full border border-outline-variant/40 bg-surface-container-low py-0.5 pl-2 pr-1 text-[11px] font-medium text-on-surface">
                      <span className="shrink-0 text-on-surface-variant">{t('Element')}</span>
                      <span className="truncate">{elementSelection.label}</span>
                      <button
                        type="button"
                        className="rounded-full p-0.5 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                        onClick={() => setElementSelection(null)}
                        aria-label={t('Clear element')}
                      >
                        <X size={11} />
                      </button>
                    </span>
                  ) : null}
                </div>
              )}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-full p-2 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                  onClick={() => fileInputRef.current?.click()}
                  title={t('Paste or attach a reference image')}
                  aria-label={t('Paste or attach a reference image')}
                >
                  <ImagePlus size={15} />
                </button>
                <input
                  className="min-w-0 flex-1 bg-transparent text-[13px] text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none"
                  placeholder={
                    canvasSelection
                      ? t('What do you want to change or create?')
                      : t('Select a card, then describe the change…')
                  }
                  value={iterateText}
                  onChange={(e) => setIterateText(e.target.value)}
                  onPaste={handlePasteImage}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void handleIterate();
                  }}
                />
                <button
                  type="button"
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-semibold transition-colors ${
                    showCodeTray
                      ? 'border-neutral-900 bg-neutral-900 text-white'
                      : 'border-outline-variant/40 bg-surface-container-low text-on-surface-variant hover:border-outline-variant hover:text-on-surface'
                  }`}
                  onClick={() => setShowCodeTray((v) => !v)}
                  title={t('Prototype → Approve → UI code → Coding')}
                  aria-expanded={showCodeTray}
                  aria-label={t('UI code')}
                >
                  <Code2 size={12} className="inline shrink-0" />
                  {t('UI code')}
                </button>
                <button
                  type="button"
                  disabled={busy || !iterateText.trim()}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-white disabled:opacity-40"
                  onClick={() => void handleIterate()}
                >
                  <ArrowUp size={14} />
                </button>
              </div>
            </div>
          </div>

          {showCodeTray ? (
            <div className="absolute right-4 top-4 z-20 w-[300px] space-y-2 rounded-2xl border border-outline-variant/30 bg-white p-3 shadow-md">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[12px] font-semibold text-on-surface">{t('UI code')}</p>
                  <p className="text-[10px] text-on-surface-variant">
                    {t('Prototype → Approve → UI code → Coding')}
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-md p-1 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                  onClick={() => setShowCodeTray(false)}
                  aria-label={t('Close')}
                >
                  <X size={14} />
                </button>
              </div>
              <p className="text-[11px] leading-relaxed text-on-surface-variant">
                {session?.prototype_approved
                  ? t('Prototype approved. Generate a Vite + React + Tailwind app.')
                  : t('Approve the prototype first.')}
              </p>
              <button
                type="button"
                className={`${BTN_SUCCESS} w-full`}
                disabled={busy || !session?.screens?.length || session.prototype_approved}
                onClick={() =>
                  void withBusy(async () => {
                    const next = await approveDesignPrototype(runId);
                    setSession(next);
                    setBusy(false);
                    return next;
                  })
                }
              >
                <Check size={14} /> {t('Approve')}
              </button>
              <button
                type="button"
                className={`${BTN_PRIMARY} w-full`}
                disabled={busy || !session?.prototype_approved}
                onClick={() =>
                  void withBusy(async () => {
                    const next = await generateDesignReact(runId);
                    setSession(next);
                    setBusy(false);
                    return next;
                  })
                }
              >
                {t('Generate UI code')}
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  className={`${BTN_SECONDARY} flex-1`}
                  disabled={busy || !session?.react_ready}
                  onClick={() =>
                    void withBusy(async () => {
                      const r = await startDesignPreview(runId);
                      setPreviewUrl(r.url);
                      setBusy(false);
                      return r;
                    })
                  }
                >
                  {t('Start preview')}
                </button>
                <button
                  type="button"
                  className={`${BTN_SECONDARY} flex-1`}
                  disabled={!previewUrl}
                  onClick={() =>
                    void withBusy(async () => {
                      await stopDesignPreview(runId);
                      setPreviewUrl(null);
                      setBusy(false);
                    })
                  }
                >
                  {t('Stop')}
                </button>
              </div>
              {previewUrl ? (
                <iframe title="preview" src={previewUrl} className="h-40 w-full rounded-xl border border-outline-variant/30" />
              ) : null}
              <button
                type="button"
                className={`${BTN_SUCCESS} w-full`}
                disabled={busy || !session?.react_ready || session.react_approved}
                onClick={() =>
                  void withBusy(async () => {
                    const next = await approveDesignReact(runId);
                    setSession(next);
                    setBusy(false);
                    return next;
                  })
                }
              >
                {t('Approve UI code')}
              </button>
              <button
                type="button"
                className={`${BTN_PRIMARY} w-full`}
                disabled={busy || !session?.react_approved}
                onClick={() =>
                  void withBusy(async () => {
                    const handoff = await sendDesignToCoding(runId);
                    onSendToCoding(handoff);
                    setBusy(false);
                    return handoff;
                  })
                }
              >
                {t('Send to Coding')}
              </button>
            </div>
          ) : null}

          {error ? (
            <div className="absolute left-1/2 top-4 z-20 -translate-x-1/2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
              {error}
            </div>
          ) : null}
        </>
      )}
    </>
  );
}

export const DesignWorkspace: React.FC<DesignWorkspaceProps> = (props) => {
  const { t } = useLanguage();
  if (!props.workspaceReady) {
    return (
      <div className="flex h-full items-center justify-center bg-surface font-sans text-sm text-neutral-500">
        {t('Authorize a workspace to use Design')}
      </div>
    );
  }

  return (
    <div className="relative h-full min-h-0 overflow-hidden bg-[#f7f7f8] font-sans" data-testid="design-workspace">
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage: 'radial-gradient(circle, #d4d4d8 1px, transparent 1px)',
          backgroundSize: '18px 18px',
        }}
      />
      <ReactFlowProvider>
        <DesignCanvasInner {...props} />
      </ReactFlowProvider>
    </div>
  );
};
