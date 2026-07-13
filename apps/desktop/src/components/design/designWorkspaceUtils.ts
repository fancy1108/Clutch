import { type Node, type Edge, Position, MarkerType } from '@xyflow/react';
import type {
  DesignSession,
  DesignRound,
  DesignSpec,
} from '../../services/designApi';
import { parseDesignRounds, designScreenVersionPath } from '../../services/designApi';

export type CanvasSelection = {
  nodeId: string;
  kind: 'ui' | 'spec' | 'md' | 'image' | 'url' | 'agentLog';
  label: string;
  screenId?: string;
};

export type ElementSelection = {
  path: string;
  label: string;
  screenId?: string;
};

export type IteratePending = {
  mode: 'modify' | 'add' | 'duplicate';
  screenId?: string | null;
};

export type SpecData = {
  phase: 'placeholder' | 'ready';
  spec?: DesignSpec | null;
  label?: string;
  designMdText?: string;
  onSaveStyle?: (name: string, designMdText: string) => void;
};

export type UiData = {
  phase: 'placeholder' | 'drawing' | 'ready';
  name: string;
  html?: string;
  previewSrc?: string | null;
  label?: string;
  screenId?: string;
  device?: 'web' | 'app';
  pickMode?: boolean;
  selectedElementPath?: string | null;
  selectedElementLabel?: string | null;
  onElementPicked?: (payload: { path: string; label: string }) => void;
  onTogglePick?: () => void;
  onDelete?: () => void;
};

export const DEVICE_VIEW = {
  web: {
    designW: 1920,
    designH: 1080,
    frameW: 720,
    frameH: 405,
  },
  app: {
    designW: 390,
    designH: 844,
    frameW: 300,
    frameH: 650,
  },
} as const;

export function deviceView(device?: string) {
  return device === 'app' ? DEVICE_VIEW.app : DEVICE_VIEW.web;
}

export const DESIGN_CANVAS_ORIGIN = 40;
export const DESIGN_AGENT_LOG_W = 272;
export const DESIGN_SPEC_W = 300;
export const DESIGN_SOURCE_W = 300;
export const DESIGN_CARD_GAP = 48;
export const DESIGN_SPEC_UI_GAP = 56;
export const DESIGN_ROW_Y = 56;

export const LAYOUT = {
  agentLog: { x: DESIGN_CANVAS_ORIGIN, y: DESIGN_ROW_Y },
  reference: { x: DESIGN_CANVAS_ORIGIN + DESIGN_AGENT_LOG_W + DESIGN_CARD_GAP, y: DESIGN_ROW_Y },
  source: { x: DESIGN_CANVAS_ORIGIN + DESIGN_AGENT_LOG_W + DESIGN_CARD_GAP, y: DESIGN_ROW_Y },
  spec: { x: DESIGN_CANVAS_ORIGIN + DESIGN_AGENT_LOG_W + DESIGN_CARD_GAP, y: DESIGN_ROW_Y },
  specAfterSource: {
    x: DESIGN_CANVAS_ORIGIN + DESIGN_AGENT_LOG_W + DESIGN_CARD_GAP + DESIGN_SOURCE_W + DESIGN_CARD_GAP,
    y: DESIGN_ROW_Y,
  },
} as const;

export function uiCanvasPos(specPos: { x: number; y: number }): { x: number; y: number } {
  return {
    x: specPos.x + DESIGN_SPEC_W + DESIGN_SPEC_UI_GAP,
    y: DESIGN_ROW_Y,
  };
}

export function stripMarkdownFences(html: string): string {
  if (!html) return html;
  return html
    .replace(/^```[\w#\-]*\s*\n?/i, '')
    .replace(/\n?```\s*$/, '')
    .trim();
}

export function ensureCharset(html: string): string {
  if (!html) return html;
  html = stripMarkdownFences(html);
  if (!html) return html;
  if (/charset\s*=/i.test(html)) return html;
  if (/<head[^>]*>/i.test(html)) {
    return html.replace(/(<head[^>]*>)/i, '$1<meta charset="utf-8"/>');
  }
  if (/<!doctype/i.test(html)) {
    return html.replace(/(<!doctype[^>]*>)/i, '$1<meta charset="utf-8"/>');
  }
  return '<meta charset="utf-8"/>' + html;
}

export function buildInteractionScript(opts: {
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
        try {
          var byFor = document.querySelector('label[for="' + el.id.replace(/"/g,'') + '"]');
          if (byFor) lab = (byFor.innerText || '').trim();
        } catch (_) {}
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

export function stripInteractionScript(html: string): string {
  return html.replace(
    /<script[^>]*data-clutch-design-interaction="1"[^>]*>[\s\S]*?<\/script>/gi,
    '',
  );
}

export function withPickerScript(
  html: string,
  opts: boolean | { pickMode?: boolean; selectedPath?: string | null },
): string {
  if (!html) return html;
  html = stripMarkdownFences(html);
  if (!html) return html;
  const pickMode = typeof opts === 'boolean' ? opts : Boolean(opts.pickMode);
  const selectedPath = typeof opts === 'boolean' ? null : opts.selectedPath || null;
  if (!pickMode && !selectedPath) {
    return stripInteractionScript(html);
  }
  const cleaned = stripInteractionScript(html);
  const script = buildInteractionScript({ pickMode, selectedPath });
  if (/<\/body>/i.test(cleaned)) {
    return cleaned.replace(/(<\/body>)/i, `${script}$1`);
  }
  return `${cleaned}${script}`;
}

export function selectionKindFromNodeId(id: string): CanvasSelection['kind'] {
  if (id === 'spec') return 'spec';
  if (id === 'mdDoc') return 'md';
  if (id === 'reference') return 'image';
  if (id === 'urlCard') return 'url';
  if (id === 'agentLog') return 'agentLog';
  if (id.startsWith('ui')) return 'ui';
  return 'spec';
}

export function selectionLabel(kind: CanvasSelection['kind'], node: Node, session: DesignSession | null): string {
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

export const IN_FLIGHT = new Set(['crafting_spec', 'generating_ui', 'iterating']);

export function isWelcomeSession(next: DesignSession): boolean {
  const hasArtifacts = Boolean(next.spec || (next.screens && next.screens.length > 0));
  const hasPrompt = Boolean(next.prompt?.trim());
  if (hasArtifacts || hasPrompt) return false;
  if (IN_FLIGHT.has(next.status)) return false;
  return next.status === 'draft' || next.phase === 'welcome' || !next.status;
}

export function hostFromUrl(url: string): string {
  try {
    return new URL(url.includes('://') ? url : `https://${url}`).hostname;
  } catch {
    return url.replace(/^https?:\/\//, '').split('/')[0] || url;
  }
}

export function autoPromptForMd(fileName: string): string {
  return `使用 the file [${fileName}] 创建设计系统。设计一个登录页面。`;
}

export function autoPromptForUrl(): string {
  return '参考这个网站，生成一个登录页面';
}

export function inferIterateModeClient(instruction: string, kind: string | undefined): 'modify' | 'add' {
  const text = instruction.toLowerCase();
  const addKeys = ['新增', '添加一', '再做', '另一个', '新页面', '新画板', 'another', 'new page', 'new screen', 'create a new'];
  if (addKeys.some((k) => text.includes(k))) return 'add';
  // Detect "生成 N 个/新 页面" or "create N pages/screens"
  if (/\u751f\u6210.*\u9875/.test(instruction) || /\u521b\u5efa.*\u9875/.test(instruction)) return 'add';
  if (/\b\d+\s*(pages?|screens?|个.*页|个.*画板)\b/.test(text)) return 'add';
  if (kind === 'ui' || !kind) return 'modify';
  return 'add';
}

export function buildCanvasNodes(
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
    screenVersions?: Record<string, number>;
    roundHtmlByScreen?: Record<string, string | undefined>;
    runId?: string;
    onElementPicked?: (payload: { path: string; label: string; screenId?: string }) => void;
    onTogglePick?: (payload: { nodeId: string; screenId: string; name: string }) => void;
    onDeleteScreen?: (screenId: string) => void;
    pasteSourceScreenIds?: Set<string> | null;
    onSaveStyle?: (name: string, designMdText: string) => void;
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
      data: { phase: 'ready', spec: session!.spec, designMdText: session?.design_md, onSaveStyle: extras?.onSaveStyle },
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
      (hasSpec && status === 'ready'));

  if (hasAnyHtml) {
    const pasteFilter = extras?.pasteSourceScreenIds;
    const visibleScreens = pasteFilter
      ? screens.filter((s) => pasteFilter.has(s.id))
      : extras?.screenVersions
        ? screens.filter((s) => (s.id || 'main') in extras.screenVersions!)
        : screens;
    visibleScreens.forEach((screen, index) => {
      if (!screen.html) return;
      const nodeId = `ui-${screen.id || index}`;
      const saved = positions[nodeId];
      const fromServer = screen.position;
      const fallbackX = uiPos.x + index * uiStep;
      const serverOk =
        fromServer &&
        typeof fromServer.x === 'number' &&
        fromServer.x >= uiPos.x - 40;
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
            : pending?.mode === 'add' && (status === 'iterating' || drawing)
              ? 'ready'
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
      const perScreenRoundIdx = extras?.screenVersions?.[screenId] ?? extras?.selectedRoundIndex ?? activeRound?.screenRoundIndex ?? 0;
      const versionedHtml = extras?.roundHtmlByScreen?.[screenId];
      const previewSrc =
        extras?.runId && perScreenRoundIdx > 0
          ? designScreenVersionPath(extras.runId, screenId, perScreenRoundIdx)
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
          onDelete: extras?.onDeleteScreen
            ? () => extras.onDeleteScreen?.(screen.id)
            : undefined,
        },
        draggable: true,
      });
    });
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
            x: uiPos.x + visibleScreens.length * uiStep,
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

export function buildCanvasEdges(nodes: Node[]): Edge[] {
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
      target: sourceId,
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

export const DESIGN_SYSTEM_PRESETS = [
  { id: 'clutch',   labelKey: 'Clutch',   descriptionKey: 'Built-in Clutch design system — clean developer-tool aesthetic', color: '#171717' },
  { id: 'airbnb', labelKey: 'Airbnb', descriptionKey: 'Travel marketplace. Warm coral accent, photography-driven, rounded UI', color: '#ff385c' },
  { id: 'airtable', labelKey: 'Airtable', descriptionKey: 'Spreadsheet-database hybrid. Colorful, friendly, structured data aesthetic', color: '#181d26' },
  { id: 'apple', labelKey: 'Apple', descriptionKey: 'Consumer electronics. Premium white space, SF Pro, cinematic imagery', color: '#0066cc' },
  { id: 'binance', labelKey: 'Binance', descriptionKey: 'Crypto exchange. Bold Binance Yellow on monochrome, trading-floor urgency', color: '#fcd535' },
  { id: 'bmw', labelKey: 'BMW', descriptionKey: 'Luxury automotive. Dark premium surfaces, precise German engineering aesthetic', color: '#1c69d4' },
  { id: 'bmw-m', labelKey: 'BMW M', descriptionKey: 'Performance automotive. Motorsport-inspired contrast, M color accents, precision-driven layout', color: '#ffffff' },
  { id: 'bugatti', labelKey: 'Bugatti', descriptionKey: 'Luxury hypercar. Cinema-black canvas, monochrome austerity, monumental display type', color: '#ffffff' },
  { id: 'cal', labelKey: 'Cal.com', descriptionKey: 'Open-source scheduling. Clean neutral UI, developer-oriented simplicity', color: '#111111' },
  { id: 'claude', labelKey: 'Claude', descriptionKey: "Anthropic's AI assistant. Warm terracotta accent, clean editorial layout", color: '#cc785c' },
  { id: 'clay', labelKey: 'Clay', descriptionKey: 'Creative agency. Organic shapes, soft gradients, art-directed layout', color: '#0a0a0a' },
  { id: 'clickhouse', labelKey: 'ClickHouse', descriptionKey: 'Fast analytics database. Yellow-accented, technical documentation style', color: '#faff69' },
  { id: 'cohere', labelKey: 'Cohere', descriptionKey: 'Enterprise AI platform. Vibrant gradients, data-rich dashboard aesthetic', color: '#17171c' },
  { id: 'coinbase', labelKey: 'Coinbase', descriptionKey: 'Crypto exchange. Clean blue identity, trust-focused, institutional feel', color: '#0052ff' },
  { id: 'composio', labelKey: 'Composio', descriptionKey: 'Tool integration platform. Modern dark with colorful integration icons', color: '#0007cd' },
  { id: 'cursor', labelKey: 'Cursor', descriptionKey: 'AI-first code editor. Sleek dark interface, gradient accents', color: '#f54e00' },
  { id: 'dell-1996', labelKey: 'Dell (1996)', descriptionKey: 'Catalog-era enterprise web. Literal black page frame, flat color-block ribbon cards, chunky Helvetica-Black titles over Times Roman body', color: '#e91d2a' },
  { id: 'elevenlabs', labelKey: 'ElevenLabs', descriptionKey: 'AI voice platform. Dark cinematic UI, audio-waveform aesthetics', color: '#000000' },
  { id: 'expo', labelKey: 'Expo', descriptionKey: 'React Native platform. Dark theme, tight letter-spacing, code-centric', color: '#000000' },
  { id: 'ferrari', labelKey: 'Ferrari', descriptionKey: 'Luxury automotive. Chiaroscuro black-white editorial, Ferrari Red with extreme sparseness', color: '#da291c' },
  { id: 'figma', labelKey: 'Figma', descriptionKey: 'Collaborative design tool. Vibrant multi-color, playful yet professional', color: '#000000' },
  { id: 'framer', labelKey: 'Framer', descriptionKey: 'Website builder. Bold black and blue, motion-first, design-forward', color: '#ffffff' },
  { id: 'hashicorp', labelKey: 'HashiCorp', descriptionKey: 'Infrastructure automation. Enterprise-clean, black and white', color: '#000000' },
  { id: 'hp', labelKey: 'HP', descriptionKey: 'PC and printer maker. Pure white canvas, HP Electric Blue signal CTA, geometric Forma DJR Micro, blue chevron decorations', color: '#024ad8' },
  { id: 'ibm', labelKey: 'IBM', descriptionKey: 'Enterprise technology. Carbon design system, structured blue palette', color: '#0f62fe' },
  { id: 'intercom', labelKey: 'Intercom', descriptionKey: 'Customer messaging. Friendly blue palette, conversational UI patterns', color: '#111111' },
  { id: 'kraken', labelKey: 'Kraken', descriptionKey: 'Crypto trading platform. Purple-accented dark UI, data-dense dashboards', color: '#7132f5' },
  { id: 'lamborghini', labelKey: 'Lamborghini', descriptionKey: 'Luxury automotive. True black cathedral, gold accent, LamboType custom Neo-Grotesk', color: '#ffc000' },
  { id: 'linear.app', labelKey: 'Linear', descriptionKey: 'Project management for engineers. Ultra-minimal, precise, purple accent', color: '#5e6ad2' },
  { id: 'lovable', labelKey: 'Lovable', descriptionKey: 'AI full-stack builder. Playful gradients, friendly dev aesthetic', color: '#f7f4ed' },
  { id: 'mastercard', labelKey: 'Mastercard', descriptionKey: 'Global payments network. Warm cream canvas, orbital pill shapes, editorial warmth', color: '#eb001b' },
  { id: 'meta', labelKey: 'Meta', descriptionKey: 'Tech retail store. Photography-first, binary light/dark surfaces, Meta Blue CTAs', color: '#0064e0' },
  { id: 'minimax', labelKey: 'Minimax', descriptionKey: 'AI model provider. Bold dark interface with neon accents', color: '#0a0a0a' },
  { id: 'mintlify', labelKey: 'Mintlify', descriptionKey: 'Documentation platform. Clean, green-accented, reading-optimized', color: '#0a0a0a' },
  { id: 'miro', labelKey: 'Miro', descriptionKey: 'Visual collaboration. Bright yellow accent, infinite canvas aesthetic', color: '#1c1c1e' },
  { id: 'mistral.ai', labelKey: 'Mistral AI', descriptionKey: 'Open-weight LLM provider. French-engineered minimalism, purple-toned', color: '#fa520f' },
  { id: 'mongodb', labelKey: 'MongoDB', descriptionKey: 'Document database. Green leaf branding, developer documentation focus', color: '#00ed64' },
  { id: 'nike', labelKey: 'Nike', descriptionKey: 'Athletic retail. Monochrome UI, massive uppercase Futura, full-bleed photography', color: '#111111' },
  { id: 'nintendo-2001', labelKey: 'Nintendo.com (2001)', descriptionKey: 'Y2K console chrome web. Brushed-periwinkle beveled metal panels, halftone-dotted carbon nav glowing amber, outlined Arial-Black box-art wordmarks', color: '#e60012' },
  { id: 'notion', labelKey: 'Notion', descriptionKey: 'All-in-one workspace. Warm minimalism, serif headings, soft surfaces', color: '#5645d4' },
  { id: 'nvidia', labelKey: 'NVIDIA', descriptionKey: 'GPU computing. Green-black energy, technical power aesthetic', color: '#76b900' },
  { id: 'ollama', labelKey: 'Ollama', descriptionKey: 'Run LLMs locally. Terminal-first, monochrome simplicity', color: '#000000' },
  { id: 'opencode.ai', labelKey: 'OpenCode AI', descriptionKey: 'AI coding platform. Developer-centric dark theme', color: '#201d1d' },
  { id: 'pinterest', labelKey: 'Pinterest', descriptionKey: 'Visual discovery platform. Red accent, masonry grid, image-first', color: '#e60023' },
  { id: 'playstation', labelKey: 'PlayStation', descriptionKey: 'Gaming console retail. Three-surface channel layout, cyan hover-scale interaction', color: '#0070d1' },
  { id: 'posthog', labelKey: 'PostHog', descriptionKey: 'Product analytics. Playful hedgehog branding, developer-friendly dark UI', color: '#f7a501' },
  { id: 'raycast', labelKey: 'Raycast', descriptionKey: 'Productivity launcher. Sleek dark chrome, vibrant gradient accents', color: '#000000' },
  { id: 'renault', labelKey: 'Renault', descriptionKey: 'French automotive. Vivid aurora gradients, NouvelR proprietary typeface, zero-radius buttons', color: '#ffed00' },
  { id: 'replicate', labelKey: 'Replicate', descriptionKey: 'Run ML models via API. Clean white canvas, code-forward', color: '#ea2804' },
  { id: 'resend', labelKey: 'Resend', descriptionKey: 'Email API for developers. Minimal dark theme, monospace accents', color: '#fcfdff' },
  { id: 'revolut', labelKey: 'Revolut', descriptionKey: 'Digital banking. Sleek dark interface, gradient cards, fintech precision', color: '#494fdf' },
  { id: 'runwayml', labelKey: 'Runway', descriptionKey: 'AI creative-tools platform with an editorial film-festival aesthetic', color: '#000000' },
  { id: 'sanity', labelKey: 'Sanity', descriptionKey: 'Headless content platform with a dark-first editorial marketing surface', color: '#0b0b0b' },
  { id: 'sentry', labelKey: 'Sentry', descriptionKey: 'Error monitoring. Dark dashboard, data-dense, pink-purple accent', color: '#150f23' },
  { id: 'shopify', labelKey: 'Shopify', descriptionKey: 'E-commerce platform. Dark-first cinematic, neon green accent, ultra-light display type', color: '#000000' },
  { id: 'slack', labelKey: 'Slack', descriptionKey: 'Team communication platform. Vibrant multi-color sidebar, clean messaging UI', color: '#4a154b' },
  { id: 'spacex', labelKey: 'SpaceX', descriptionKey: 'Space technology. Stark black and white, full-bleed imagery, futuristic', color: '#000000' },
  { id: 'spotify', labelKey: 'Spotify', descriptionKey: 'Music streaming. Vibrant green on dark, bold type, album-art-driven', color: '#1ed760' },
  { id: 'starbucks', labelKey: 'Starbucks', descriptionKey: 'Coffee retail flagship. Four-tier earth-green system, warm cream canvas, proprietary SoDoSans typography', color: '#006241' },
  { id: 'stripe', labelKey: 'Stripe', descriptionKey: 'Payment infrastructure. Signature purple gradients, weight-300 elegance', color: '#533afd' },
  { id: 'supabase', labelKey: 'Supabase', descriptionKey: 'Open-source Firebase alternative. Dark emerald theme, code-first', color: '#3ecf8e' },
  { id: 'superhuman', labelKey: 'Superhuman', descriptionKey: 'Fast email client. Premium dark UI, keyboard-first, purple glow', color: '#1b1938' },
  { id: 'tesla', labelKey: 'Tesla', descriptionKey: 'Electric vehicles. Radical subtraction, cinematic full-viewport photography, Universal Sans', color: '#3e6ae1' },
  { id: 'theverge', labelKey: 'The Verge', descriptionKey: 'Tech editorial media. Acid-mint and ultraviolet accents, Manuka display type', color: '#3cffd0' },
  { id: 'together.ai', labelKey: 'Together AI', descriptionKey: 'Open-source AI infrastructure. Technical, blueprint-style design', color: '#000000' },
  { id: 'uber', labelKey: 'Uber', descriptionKey: 'Mobility platform. Bold black and white, tight type, urban energy', color: '#000000' },
  { id: 'vercel', labelKey: 'Vercel', descriptionKey: 'Frontend deployment platform. Black and white precision, Geist font', color: '#171717' },
  { id: 'vodafone', labelKey: 'Vodafone', descriptionKey: 'Global telecom brand. Monumental uppercase display, Vodafone Red chapter bands', color: '#e60000' },
  { id: 'voltagent', labelKey: 'VoltAgent', descriptionKey: 'AI agent framework. Void-black canvas, emerald accent, terminal-native', color: '#00d992' },
  { id: 'warp', labelKey: 'Warp', descriptionKey: 'Modern terminal. Dark IDE-like interface, block-based command UI', color: '#f7f5f0' },
  { id: 'webflow', labelKey: 'Webflow', descriptionKey: 'Visual web builder. Blue-accented, polished marketing site aesthetic', color: '#080808' },
  { id: 'wired', labelKey: 'WIRED', descriptionKey: 'Tech magazine. Paper-white broadsheet density, custom serif, ink-blue links', color: '#000000' },
  { id: 'wise', labelKey: 'Wise', descriptionKey: 'International money transfer. Bright green accent, friendly and clear', color: '#9fe870' },
  { id: 'x.ai', labelKey: 'xAI', descriptionKey: "Elon Musk's AI lab. Stark monochrome, futuristic minimalism", color: '#ffffff' },
  { id: 'zapier', labelKey: 'Zapier', descriptionKey: 'Automation platform. Warm orange, friendly illustration-driven', color: '#ff4f00' },
] as const;

export type DesignSystemId = (typeof DESIGN_SYSTEM_PRESETS)[number]['id'];
