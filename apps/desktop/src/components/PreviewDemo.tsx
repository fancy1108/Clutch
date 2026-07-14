import React, { useEffect, useState, useRef } from 'react';
import { Layers, Tv, Activity, HelpCircle, CheckCircle, ChevronDown, ArrowLeft, ArrowRight, X, Plus, Edit, Pencil, Code } from 'lucide-react';
import StateController from './StateController';
import MatrixPreview from './MatrixPreview';
import { DesignScreen } from '../services/designApi';
import { useLanguage } from './LanguageContext';
import { sidecarFetch, sidecarHttpUrl } from '../services/sidecarUrl';

interface PreviewDemoProps {
  screens: DesignScreen[];
  sessionRunId?: string;
}

function extractElementsFromHtml(html: string): Array<{ type: string; text: string }> {
  if (!html) return [];
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const elements: Array<{ type: string; text: string }> = [];

    // Extract buttons
    doc.querySelectorAll('button, a').forEach((el) => {
      const text = el.textContent?.trim() || '';
      if (text.length > 0) {
        elements.push({ type: 'button', text });
      }
    });

    // Extract headers
    doc.querySelectorAll('h1, h2, h3, h4').forEach((el) => {
      const text = el.textContent?.trim() || '';
      if (text.length > 0) {
        elements.push({ type: 'heading', text });
      }
    });

    return elements;
  } catch (e) {
    return [];
  }
}

function buildSimulatorSrcDoc(html: string) {
  if (!html) return '';

  // Impeccable Viewport Adapter styling to force static pages to wrap and be fluid
  const adapterStyle = `
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
      html, body {
        width: 100% !important;
        max-width: 100% !important;
        margin: 0 !important;
        padding: 16px !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
      }
      *, *:before, *:after {
        box-sizing: border-box !important;
      }
      /* Standard fix for containers with hardcoded widths */
      div, form, section, main, header, footer {
        max-width: 100% !important;
      }
      img, svg {
        max-width: 100% !important;
        height: auto !important;
      }
    </style>
  `;

  let processed = html;
  if (processed.includes('</head>')) {
    return processed.replace('</head>', `${adapterStyle}</head>`);
  }
  return adapterStyle + processed;
}

export default function PreviewDemo({ screens, sessionRunId }: PreviewDemoProps) {
  const { t } = useLanguage();
  const [payload, setPayload] = useState<any>(null);
  const [state, setState] = useState('Normal');
  const [extreme, setExtreme] = useState(false);
  const [viewports] = useState(['2560', '1440', '390']);
  const [activeScreenId, setActiveScreenId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'simulator' | 'matrix' | 'flows'>('simulator');
  const [deviceMode, setDeviceMode] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');
  const [loading, setLoading] = useState(true);
  const [isScreenDropdownOpen, setIsScreenDropdownOpen] = useState(false);
  const screenDropdownRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [clickableCount, setClickableCount] = useState(0);
  const [mutableFlows, setMutableFlows] = useState<any[]>([]);
  const mutableFlowsRef = useRef<any[]>([]);
  const [editMode, setEditMode] = useState(false);
  const [contextMenu, setContextMenu] = useState<{
    flow: any | null;
    elementText: string;
    x: number; y: number;
  } | null>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const [connectionLines, setConnectionLines] = useState<Array<{
    fromX: number; fromY: number; toX: number; toY: number; flow: any;
  }>>([]);
  const linesContainerRef = useRef<HTMLDivElement>(null);
  const sidebarScrollRef = useRef<HTMLDivElement>(null);
  const [dragLine, setDragLine] = useState<{
    fromX: number; fromY: number;
    mouseX: number; mouseY: number;
    sourceElementText: string;
    existingFlow: any | null;
  } | null>(null);

  // Keep ref in sync so click-time lookups always use latest flows
  useEffect(() => { mutableFlowsRef.current = mutableFlows; }, [mutableFlows]);

  // Auto-save flows to interaction contract on disk when they change
  useEffect(() => {
    if (!sessionRunId || mutableFlows.length === 0) return;
    const url = sidecarHttpUrl(`/api/design/sessions/${encodeURIComponent(sessionRunId)}/contract`);
    sidecarFetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ flows: mutableFlows }),
    }).catch(() => {}); // fire-and-forget
  }, [mutableFlows, sessionRunId]);

  // ---- Prototype Navigation History ----
  const [navigationStack, setNavigationStack] = useState<string[]>([]);
  const [navigationIndex, setNavigationIndex] = useState(-1);

  const navigateTo = React.useCallback((screenId: string) => {
    setNavigationStack((prev) => {
      const trimmed = prev.slice(0, navigationIndex + 1);
      if (trimmed[trimmed.length - 1] === screenId) return trimmed;
      return [...trimmed, screenId];
    });
    setNavigationIndex((prev) => prev + 1);
    setActiveScreenId(screenId);
    setIsScreenDropdownOpen(false);
  }, [navigationIndex]);

  const goBack = React.useCallback(() => {
    if (navigationIndex <= 0) return;
    const newIndex = navigationIndex - 1;
    setNavigationIndex(newIndex);
    setActiveScreenId(navigationStack[newIndex]);
  }, [navigationIndex, navigationStack]);

  const goForward = React.useCallback(() => {
    if (navigationIndex >= navigationStack.length - 1) return;
    const newIndex = navigationIndex + 1;
    setNavigationIndex(newIndex);
    setActiveScreenId(navigationStack[newIndex]);
  }, [navigationIndex, navigationStack]);

  // Close screen dropdown & context menu on click outside
  useEffect(() => {
    function clickOutside(e: MouseEvent) {
      if (screenDropdownRef.current && !screenDropdownRef.current.contains(e.target as Node)) {
        setIsScreenDropdownOpen(false);
      }
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) {
        setContextMenu(null);
      }
    }
    document.addEventListener('mousedown', clickOutside);
    return () => document.removeEventListener('mousedown', clickOutside);
  }, []);

  // Convert actual screens to boards payload format
  const boards = React.useMemo(() => {
    return screens.map((s) => ({
      id: s.id,
      title: s.name,
      elements: extractElementsFromHtml(s.html || '')
    }));
  }, [screens]);

  useEffect(() => {
    if (screens.length > 0 && !activeScreenId) {
      const firstId = screens[0].id;
      setActiveScreenId(firstId);
      setNavigationStack([firstId]);
      setNavigationIndex(0);
    }
  }, [screens, activeScreenId]);

  useEffect(() => {
    if (boards.length === 0) {
      setLoading(false);
      return;
    }

    setLoading(true);
    // Fetch suggested flows, matrix layouts, and state injections from orchestrator preview API
    const body = {
      boards: boards,
      state_definitions: {
        Normal: { overrides: {} },
        Warning: { overrides: { color: 'amber' } },
        Critical: { overrides: { color: 'red', border: 'red' } },
        DataOverflow: { overrides: { text: '99999999.99' } }
      },
      preview_options: { extreme: extreme, viewports: viewports }
    };

    sidecarFetch(sidecarHttpUrl('/api/preview/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then((r) => r.json())
      .then((data) => {
        setPayload(data);
        // Try to restore saved contract from disk, fall back to API-generated flows
        let flows = data.flows || [];
        if (sessionRunId) {
          const contractUrl = sidecarHttpUrl(`/api/design/sessions/${encodeURIComponent(sessionRunId)}/contract`);
          sidecarFetch(contractUrl)
            .then(r => r.json())
            .then(contract => {
              if (contract.interactions && Array.isArray(contract.interactions) && contract.interactions.length > 0) {
                setMutableFlows(contract.interactions);
                setLoading(false);
              } else {
                setMutableFlows(flows);
                setLoading(false);
              }
            })
            .catch(() => { setMutableFlows(flows); setLoading(false); });
        } else {
          setMutableFlows(flows);
          setLoading(false);
        }
        setLoading(false);
      })
      .catch((e) => {
        console.warn('[PreviewDemo] API call failed:', e);
        setPayload({ error: String(e), flows: [] });
        setMutableFlows([]);
        setLoading(false);
      });
  }, [boards, extreme, viewports]);

  // Compute Simulator Iframe sizing and scale factor dynamically to fit container height/width
  const { simWidth, simHeight, cardWidth, cardHeight, scale } = React.useMemo(() => {
    const H = 390; // available height inside container (leaves vertical padding)
    const W = 660; // available width inside container (leaves horizontal padding)

    let w = 1440;
    let h = 900;

    if (deviceMode === 'mobile') {
      w = 390;
      h = 844;
    } else if (deviceMode === 'tablet') {
      w = 1024;
      h = 1366;
    }

    const scaleW = W / w;
    const scaleH = H / h;
    const s = Math.min(scaleW, scaleH);

    return {
      simWidth: w,
      simHeight: h,
      cardWidth: Math.round(w * s),
      cardHeight: Math.round(h * s),
      scale: s
    };
  }, [deviceMode]);

  // Thumbnail iframe dimensions — follow deviceMode so left panel mirrors the right simulator.
  // Each mode gets its own scale + container height to keep thumbnails legible regardless of aspect ratio.
  const thumbDims = React.useMemo(() => {
    let w: number, h: number, s: number, ch: string;
    if (deviceMode === 'mobile') {
      w = 390; h = 844;
      s = 0.178;          // visible ~69×150px, fills sidebar width well
      ch = 'h-36';        // 144px container
    } else if (deviceMode === 'tablet') {
      w = 1024; h = 1366;
      s = 0.088;          // visible ~90×120px
      ch = 'h-28';        // 112px container
    } else {
      w = 1440; h = 900;
      s = 0.072;          // visible ~104×65px
      ch = 'h-16';        // 64px container
    }
    return { width: w, height: h, scale: s, containerH: ch };
  }, [deviceMode]);

  // Auto-detect mobile / tablet from prototype HTML on first load.
  // Only check signals that are mobile-specific — NOT generic responsive meta tags
  // like viewport width=device-width (used by desktop sites too).
  useEffect(() => {
    if (screens.length === 0) return;
    const firstHtml = screens[0].html || '';
    if (!firstHtml) return;
    // Mobile-specific signals (not present in responsive desktop pages):
    const hasMobileViewport =
      /user-scalable=no/.test(firstHtml)                        // mobile web-app lock
      || /viewport[^>]*content="[^"]*\bwidth=(3[0-9]{2}|4[0-3][0-9])\b/.test(firstHtml)  // explicit mobile width
      || /max-width:\s*(3[0-9]{2}|4[0-3][0-9])\s*px/.test(firstHtml);                    // CSS mobile container
    if (hasMobileViewport) {
      setDeviceMode('mobile');
    }
  }, []); // run once on mount

  // Direct, safe external DOM modification to avoid script strings leak
  const applyStateToIframe = (iframe: HTMLIFrameElement) => {
    try {
      const doc = iframe.contentDocument || iframe.contentWindow?.document;
      if (!doc || !doc.body) return;

      // 1. Clear old banners
      const oldBanners = doc.querySelectorAll('.clutch-preview-banner');
      oldBanners.forEach(b => b.remove());

      // 2. Restore inputs styling
      const inputs = doc.querySelectorAll('input, select, textarea');
      inputs.forEach(input => {
        (input as HTMLElement).style.borderColor = '';
        (input as HTMLElement).style.boxShadow = '';
      });

      // 3. Find target main container card
      let container: HTMLElement = doc.body;
      const card = doc.querySelector('form, [class*="card"], [class*="container"], [class*="login"], main');
      if (card) {
        container = card as HTMLElement;
      }

      const metrics = doc.querySelectorAll('[data-role="metric"], .metric, .metric-card, h1, h2');

      // 4. Inject Feedback Banners
      if (state === 'Warning') {
        const banner = doc.createElement('div');
        banner.className = 'clutch-preview-banner';
        banner.style.cssText = 'background:#fffbeb; border:1px solid #f59e0b; padding:8px 12px; border-radius:8px; margin-bottom:12px; font-size:10px; color:#b45309; font-weight:500; display:flex; align-items:center; gap:6px; box-shadow:0 1px 2px rgba(0,0,0,0.05);';
        if (inputs.length > 0) {
          banner.innerHTML = '<span>⚠️</span> <span>' + t('Form input processing may be delayed') + '</span>';
        } else if (metrics.length > 0) {
          banner.innerHTML = '<span>⚠️</span> <span>' + t('Data metrics loading slowly') + '</span>';
        } else {
          banner.innerHTML = '<span>⚠️</span> <span>' + t('Page data is loading slowly') + '</span>';
        }
        container.insertBefore(banner, container.firstChild);
      } else if (state === 'Critical') {
        const banner = doc.createElement('div');
        banner.className = 'clutch-preview-banner';
        banner.style.cssText = 'background:#fff1f2; border:1px solid #f43f5e; padding:8px 12px; border-radius:8px; margin-bottom:12px; font-size:10px; color:#b91c1c; font-weight:500; display:flex; align-items:center; gap:6px; box-shadow:0 1px 2px rgba(0,0,0,0.05);';
        if (inputs.length > 0) {
          banner.innerHTML = '<span>❌</span> <span>' + t('Validation failed, please check and try again') + '</span>';
          inputs.forEach(input => {
            (input as HTMLElement).style.borderColor = '#f43f5e';
            (input as HTMLElement).style.boxShadow = '0 0 0 1px #f43f5e';
          });
        } else if (metrics.length > 0) {
          banner.innerHTML = '<span>❌</span> <span>' + t('Data service connection timeout') + '</span>';
        } else {
          banner.innerHTML = '<span>❌</span> <span>' + t('Request failed, please try again later') + '</span>';
        }
        container.insertBefore(banner, container.firstChild);
      }

      // 5. Data Overflow variables replacement
      if (state === 'DataOverflow') {
        const walk = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
        let node;
        while (node = walk.nextNode()) {
          if (node.parentNode && (node.parentNode as HTMLElement).closest('script, style')) continue;
          if (/\d+/.test(node.nodeValue || '')) {
            node.nodeValue = (node.nodeValue || '').replace(/\d+([.,]\d+)?/g, '99,999,999.99');
          }
        }
      }

      // 6. Extreme variables stress testing
      if (extreme) {
        inputs.forEach(tf => {
          if (tf.tagName === 'INPUT' && ((tf as HTMLInputElement).type === 'text' || (tf as HTMLInputElement).type === 'email')) {
            (tf as HTMLInputElement).value = 'user_dynamic_input_stress_test_overflow_long_string_value_99999999@clutch.io';
          }
        });

        const walk = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
        let node;
        const textNodes: Node[] = [];
        while (node = walk.nextNode()) {
          textNodes.push(node);
        }
        textNodes.forEach(n => {
          const val = (n.nodeValue || '').trim();
          if (val.length > 0) {
            const parent = n.parentNode;
            if (parent) {
              const element = parent as HTMLElement;
              if (element.closest('script, style')) return;
              const isStaticTemplate = element.closest('button') || element.closest('a') || element.tagName === 'LABEL' || 
                ['sign in', 'welcome back', 'forgot password', 'email', 'username', 'password'].includes(val.toLowerCase());
              
              if (!isStaticTemplate) {
                if (/\d+/.test(val)) {
                  n.nodeValue = '9,999,999,999.99';
                } else if (val.length > 15) {
                  n.nodeValue = val + ' LONG_STRESS_TEXT_OVERFLOW';
                }
              }
            }
          }
        });
      }
    } catch (e) {
      /* Handle cross-origin or load cycle catches */
    }
  };

  // ---- Prototype Click Injection: make IUE-inferred elements clickable ----
  const injectPrototypeClickHandlers = React.useCallback((iframe: HTMLIFrameElement) => {
    try {
      const doc = iframe.contentDocument || iframe.contentWindow?.document;
      if (!doc || !doc.body) { setClickableCount(0); return; }

      // 0) Clear previous clickable state
      doc.querySelectorAll('[data-clutch-clickable]').forEach((el) => {
        const h = el as HTMLElement;
        h.removeAttribute('data-clutch-clickable');
        h.style.cursor = '';
        h.style.outline = '';
        h.style.outlineOffset = '';
        h.onclick = null;
      });

      const outboundFlows = mutableFlows.filter((f: any) => f.from === activeScreenId);
      const flowByText: Map<string, string> = new Map();
      for (const f of outboundFlows) {
        const key = (f.source_element_text || '').toLowerCase().trim();
        if (!key) continue;
        flowByText.set(key, f.to);
      }

      let injected = 0;
      // Use broad selector in both modes — user may have connected any element
      const sel = 'button, a, [role="button"], input[type="submit"], input[type="button"], li, [class*="menu"], [class*="nav"], [class*="sidebar"] a, [class*="sidebar"] li, nav *';
      const seen = new Set<HTMLElement>();
      doc.querySelectorAll(sel).forEach((el) => {
        // In edit mode, skip tiny/invisible elements and nested children of already-seen
        if (editMode) {
          const htmlEl = el as HTMLElement;
          const rect = htmlEl.getBoundingClientRect();
          if (rect.width < 20 || rect.height < 10) return; // too small
          // Check if any ancestor is already processed
          let p = htmlEl.parentElement;
          while (p) { if (seen.has(p)) return; p = p.parentElement; }
          seen.add(htmlEl);
        }
        const rawText = (el.textContent || (el as HTMLInputElement).value || '').trim();
        if (!rawText) return;
        const rawLower = rawText.toLowerCase();

        let existingFlow: any = null;
        if (flowByText.has(rawLower)) {
          const tid = flowByText.get(rawLower)!;
          existingFlow = outboundFlows.find(f => f.to === tid) || null;
        } else {
          for (const [ft, tid] of flowByText) {
            if (rawLower.includes(ft) || ft.includes(rawLower)) {
              existingFlow = outboundFlows.find(f => f.to === tid) || null;
              break;
            }
          }
        }

        const htmlEl = el as HTMLElement;
        htmlEl.setAttribute('data-clutch-clickable', existingFlow ? existingFlow.to : 'new');
        htmlEl.style.cursor = 'pointer';
        htmlEl.style.outline = existingFlow
          ? '2px solid rgba(59,130,246,0.4)'
          : editMode
            ? '2px dashed rgba(148,163,184,0.5)'
            : '';
        htmlEl.style.outlineOffset = '2px';

        const elRect = htmlEl.getBoundingClientRect();
        htmlEl.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (editMode) {
            if (!existingFlow) {
              // No existing flow → start drag from element CENTER (not mouse position)
              const lc = linesContainerRef.current?.getBoundingClientRect();
              const ifr = iframeRef.current?.getBoundingClientRect();
              const elCenterX = ifr ? ifr.left + elRect.left * scale + elRect.width * scale / 2 : e.clientX;
              const elCenterY = ifr ? ifr.top + elRect.top * scale + elRect.height * scale / 2 : e.clientY;
              setDragLine({
                fromX: lc ? elCenterX - lc.left : elCenterX,
                fromY: lc ? elCenterY - lc.top : elCenterY,
                mouseX: lc ? elCenterX - lc.left : elCenterX,
                mouseY: lc ? elCenterY - lc.top : elCenterY,
                sourceElementText: rawText,
                existingFlow: null,
              });
            } else {
              // Has flow → open context menu for edit/delete
              setContextMenu({
                flow: existingFlow,
                elementText: rawText,
                x: Math.min(elRect.right + 6, window.innerWidth - 180),
                y: Math.min(elRect.top, window.innerHeight - 280),
              });
            }
          } else {
            // Preview mode: navigate if has flow
            const cur = mutableFlowsRef.current.filter((f: any) => f.from === activeScreenId);
            const m = cur.find((f: any) =>
              (f.source_element_text || '').toLowerCase().trim() === rawLower ||
              rawLower.includes((f.source_element_text || '').toLowerCase()) ||
              (f.source_element_text || '').toLowerCase().includes(rawLower)
            );
            if (m) navigateTo(m.to);
          }
        };
        injected++;
      });
      setClickableCount(injected);
    } catch (_) { setClickableCount(0); }
  }, [mutableFlows, activeScreenId, editMode, navigateTo, screens]);

  // Re-trigger DOM style applications and click injection when react states shift
  useEffect(() => {
    if (iframeRef.current) {
      applyStateToIframe(iframeRef.current);
      injectPrototypeClickHandlers(iframeRef.current);
    }
  }, [state, extreme, activeScreenId, editMode, injectPrototypeClickHandlers]);

  // ---- Calculate connection lines in edit mode (rAF ensures DOM is ready) ----
  const calcLines = React.useCallback(() => {
    if (!editMode || !iframeRef.current || !linesContainerRef.current) {
      setConnectionLines([]);
      return;
    }
    const container = linesContainerRef.current;
    const containerRect = container.getBoundingClientRect();
    const sidebar = sidebarScrollRef.current;
    const sidebarRect = sidebar?.getBoundingClientRect();
    const iframe = iframeRef.current;
    const iframeRect = iframe.getBoundingClientRect();
    const doc = iframe.contentDocument;
    if (!doc || !sidebarRect) { setConnectionLines([]); return; }

    const outboundFlows = mutableFlows.filter((f: any) => f.from === activeScreenId);
    const lines: Array<{fromX:number;fromY:number;toX:number;toY:number;flow:any;offscreen?:boolean}> = [];

    for (const flow of outboundFlows) {
      const hotZones = doc.querySelectorAll('[data-clutch-clickable]');
      for (const el of hotZones) {
        const text = ((el as HTMLElement).textContent || '').trim().toLowerCase();
        const ft = (flow.source_element_text || '').toLowerCase();
        if (!text || !ft) continue;
        if (text !== ft && !text.includes(ft) && !ft.includes(text)) continue;

        const elRect = (el as HTMLElement).getBoundingClientRect();
        const fromX = iframeRect.left - containerRect.left + elRect.left * scale + elRect.width * scale / 2;
        const fromY = iframeRect.top - containerRect.top + elRect.top * scale + elRect.height * scale / 2;

        const thumb = document.querySelector(`[data-screen-id="${flow.to}"]`);
        if (thumb) {
          const tr = thumb.getBoundingClientRect();
          let toX = tr.right - containerRect.left;
          let toY = tr.top - containerRect.top + tr.height / 2;
          let offscreen = false;
          // Clamp Y if target thumbnail is scrolled outside sidebar visible area
          const sidebarTop = sidebarRect.top - containerRect.top;
          const sidebarBottom = sidebarRect.bottom - containerRect.top;
          if (toY < sidebarTop + 10) {
            toY = sidebarTop + 10;
            offscreen = true;
          } else if (toY > sidebarBottom - 10) {
            toY = sidebarBottom - 10;
            offscreen = true;
          }
          lines.push({ fromX, fromY, toX, toY, flow, offscreen });
        }
        break;
      }
    }
    setConnectionLines(lines);
  }, [editMode, activeScreenId, mutableFlows, scale, clickableCount]);

  // Recalculate lines after DOM settles + on sidebar scroll
  useEffect(() => {
    if (!editMode) { setConnectionLines([]); return; }
    const id = requestAnimationFrame(() => calcLines());
    // Also recalculate on sidebar scroll
    const sidebar = sidebarScrollRef.current;
    let ticking = false;
    const onScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => { calcLines(); ticking = false; });
        ticking = true;
      }
    };
    sidebar?.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(id);
      sidebar?.removeEventListener('scroll', onScroll);
    };
  }, [calcLines, editMode]);

  const [generatingCode, setGeneratingCode] = useState(false);
  const [codeGenResult, setCodeGenResult] = useState<{written:number;path:string} | null>(null);
  const [copyingPrompt, setCopyingPrompt] = useState(false);
  const [pathCopied, setPathCopied] = useState(false);
  

  const generateCode = async () => {
    if (!sessionRunId) return;
    setGeneratingCode(true);
    try {
      const url = sidecarHttpUrl(`/api/design/sessions/${encodeURIComponent(sessionRunId)}/generate-code/write`);
      const r = await sidecarFetch(url, { method: 'POST' });
      const data = await r.json();
      setCodeGenResult(data);
    } catch (e) {
      alert('Code generation failed: ' + String(e));
    } finally {
      setGeneratingCode(false);
    }
  };

  const copyPath = () => {
    if (!codeGenResult) return;
    navigator.clipboard.writeText(codeGenResult.path).then(() => {
      setPathCopied(true);
      setTimeout(() => setPathCopied(false), 1500);
    });
  };

  const aiPrompt = codeGenResult
    ? `I have a React project generated from a Clutch design prototype. Please integrate these components into a working app.

**Interaction Contract (SSOT — defines all navigation):**
${sessionRunId ? `.clutch/design/sessions/${sessionRunId}/interaction_contract.json` : '(contract not available)'}
- Read this first. Every entry maps a button/link text to its target page.
- For each interaction: wrap the matched element with an onClick that navigates to the target.

**Generated components (HTML to JSX):**
./generated/
- Per-screen React components with Tailwind styling.
- Contract source_element_text values match button/link text in these files.

**Requirements:**
1. npm install && npm run dev to verify it runs
2. Set up routing based on contract page transitions
3. Every interaction in the contract MUST be implemented
4. Keep all existing Tailwind styles
5. The app should be fully navigable end-to-end`
    : '';

  if (screens.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-6 text-center select-none bg-surface-bright text-on-surface">
        <HelpCircle size={44} className="text-on-surface-variant/40 mb-3" />
        <p className="text-xs font-bold text-on-surface-variant">{t('No screens available for preview')}</p>
        <p className="text-[11px] text-on-surface-variant/60 max-w-sm mt-1 leading-normal">
          {t('No screens generated in this session yet...')}
        </p>
      </div>
    );
  }

  if (loading && !payload) {
    return (
      <div className="flex flex-col items-center justify-center py-24 select-none bg-surface-bright">
        <div className="animate-spin rounded-full h-7 w-7 border-b-2 border-primary"></div>
        <span className="text-[11px] text-on-surface-variant/60 mt-3 font-medium">{t('Parsing boards and generating flows...')}</span>
      </div>
    );
  }

  // Find active screen details
  const activeScreen = screens.find((s) => s.id === activeScreenId);
  const activeFlows = mutableFlows.filter((f: any) => f.from === activeScreenId);

  const deleteFlow = (flow: any) => {
    setMutableFlows(prev => prev.filter(f => !(f.from === flow.from && f.to === flow.to && f.source_element_text === flow.source_element_text)));
    setContextMenu(null);
  };

  const addFlowForElement = (elementText: string, targetId: string) => {
    if (!targetId || targetId === activeScreenId || !elementText.trim()) return;
    setMutableFlows(prev => [...prev, {
      from: activeScreenId, to: targetId, trigger: 'click',
      confidence: 1.0, reason: t('Manually added connection'),
      source_element_text: elementText.trim(),
      source_element_role: 'Unknown', params: {}, status: 'approved',
    }]);
    setContextMenu(null);
  };

  const editFlowTarget = (flow: any, newTarget: string) => {
    if (!newTarget || newTarget === activeScreenId) return;
    setMutableFlows(prev => prev.map(f =>
      (f.from === flow.from && f.to === flow.to && f.source_element_text === flow.source_element_text)
        ? { ...f, to: newTarget, reason: '用户编辑的目标页面' }
        : f
    ));
    setContextMenu(null);
  };

  return (
    <div className="flex flex-col h-full bg-surface-dim rounded-[20px] overflow-hidden border border-outline/40">
      {/* State & Configuration Bar */}
      <div className="bg-surface-bright border-b border-outline/35 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 shrink-0">
        {/* Tab Controls (Moved to Left) */}
        <div className="inline-flex items-center bg-surface p-1 rounded-lg border border-outline/40 select-none">
          <button
            onClick={() => setActiveTab('simulator')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'simulator'
                ? 'bg-surface-bright text-on-surface shadow-xs border border-outline/45'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/40 border border-transparent'
            }`}
          >
            <Tv size={13} />
            {t('Interactive Simulator')}
          </button>
          <button
            onClick={() => setActiveTab('matrix')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'matrix'
                ? 'bg-surface-bright text-on-surface shadow-xs border border-outline/45'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/40 border border-transparent'
            }`}
          >
            <Layers size={13} />
            {t('Multi-Viewport Matrix')}
          </button>
          <button
            onClick={() => setActiveTab('flows')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'flows'
                ? 'bg-surface-bright text-on-surface shadow-xs border border-outline/45'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/40 border border-transparent'
            }`}
          >
            <Activity size={13} />
            {t('Logic Connections Chart')} ({mutableFlows.length})
          </button>
        </div>

        {/* States & Options (Moved to Top Right) */}
        <div className="flex items-center gap-4">
          <StateController state={state} setState={setState} />
          
          <label className="inline-flex items-center gap-1.5 cursor-pointer text-[10px] font-medium text-on-surface-variant select-none hover:text-on-surface transition-colors">
            <input
              type="checkbox"
              checked={extreme}
              onChange={(e) => setExtreme(e.target.checked)}
              className="rounded border-outline/40 text-primary focus:ring-primary/50 w-3 h-3 cursor-pointer"
            />
            <span>{t('Extreme Mode')}</span>
          </label>

        </div>
      </div>

      {/* Main Tab Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'simulator' && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 h-full min-h-[420px]">
            {/* Simulator Sidebar */}
            <div className="md:col-span-1 bg-surface p-4 border border-outline/35 rounded-2xl flex flex-col gap-4 shadow-xs select-none h-[510px]">
              {/* Screen Thumbnail List */}
              <div ref={sidebarScrollRef} className="flex-1 overflow-auto space-y-2 pr-2">
                {screens.map(s => {
                  const isActive = s.id === activeScreenId;
                  const outCount = mutableFlows.filter((f: any) => f.from === s.id).length;
                  const inCount = mutableFlows.filter((f: any) => f.to === s.id).length;
                  return (
                    <button
                      key={s.id}
                      data-screen-id={s.id}
                      onClick={() => navigateTo(s.id)}
                      className={`w-full text-left overflow-hidden cursor-pointer group transition-all ${
                        deviceMode === 'mobile'
                          ? 'rounded-[18px] border-2 border-neutral-400/60'
                          : deviceMode === 'tablet'
                          ? 'rounded-[14px] border'
                          : 'rounded-xl border'
                      } ${
                        isActive
                          ? 'border-primary/50 bg-primary/5 shadow-sm'
                          : deviceMode === 'mobile'
                          ? 'bg-surface hover:border-neutral-400'
                          : 'border-outline/50 bg-surface hover:border-outline/60 hover:bg-surface-container-low'
                      }`}
                    >
                      {/* Mini preview iframe */}
                      <div className={`${thumbDims.containerH} overflow-hidden relative ${
                        deviceMode === 'mobile'
                          ? 'bg-neutral-100 rounded-t-[14px]'
                          : 'bg-neutral-50 border-b border-outline/20'
                      }`}>
                        {/* Phone notch for mobile thumbnails */}
                        {deviceMode === 'mobile' && (
                          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-7 h-1.5 bg-neutral-300 rounded-b-full z-10" />
                        )}
                        {s.html ? (
                          <iframe
                            srcDoc={buildSimulatorSrcDoc(s.html)}
                            className="border-none absolute top-0 left-0 pointer-events-none"
                            style={{
                              width: `${thumbDims.width}px`, height: `${thumbDims.height}px`,
                              transform: `scale(${thumbDims.scale})`,
                              transformOrigin: 'top left',
                            }}
                            sandbox="allow-scripts"
                          />
                        ) : (
                          <div className="flex items-center justify-center h-full text-[9px] text-on-surface-variant/30 italic">
                            No preview
                          </div>
                        )}
                      </div>
                      {/* Label + flow counts */}
                      <div className="px-2.5 py-2 flex items-center justify-between">
                        <span className={`text-[10px] font-semibold truncate max-w-[60%] ${
                          isActive ? 'text-primary' : 'text-on-surface'
                        }`}>
                          {s.name || s.id}
                        </span>
                        <span className="text-[9px] text-on-surface-variant/40 shrink-0 flex gap-1">
                          {outCount > 0 && <span className="text-blue-500/70">{t('Out')}{outCount}</span>}
                          {inCount > 0 && <span className="text-green-500/70">{t('In')}{inCount}</span>}
                        </span>
                      </div>
                    </button>
                  );
                })}

              </div>
            </div>

            {/* Live Interactive Screen Simulator (Iframe Mockup View) */}
            <div className="md:col-span-3 flex flex-col bg-surface border border-outline/35 rounded-2xl shadow-xs overflow-hidden h-[510px]">
              {/* Simulator Header */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-outline/30 bg-surface-bright shrink-0 select-none">
                <div className="flex items-center gap-1.5">
                  {/* Navigation Breadcrumb */}
                  <button
                    onClick={goBack}
                    disabled={navigationIndex <= 0}
                    className="p-0.5 rounded hover:bg-surface-container-high transition-colors disabled:opacity-25 disabled:cursor-default cursor-pointer"
                    title="后退"
                  >
                    <ArrowLeft size={12} className="text-on-surface-variant" />
                  </button>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                    {activeScreen?.name}
                  </span>
                  <button
                    onClick={goForward}
                    disabled={navigationIndex >= navigationStack.length - 1}
                    className="p-0.5 rounded hover:bg-surface-container-high transition-colors disabled:opacity-25 disabled:cursor-default cursor-pointer"
                    title="前进"
                  >
                    <ArrowRight size={12} className="text-on-surface-variant" />
                  </button>
                  {navigationStack.length > 1 && (
                    <span className="text-[9px] text-on-surface-variant/40 ml-1">
                      ({navigationIndex + 1}/{navigationStack.length})
                    </span>
                  )}

                </div>

                {/* Toolbar: edit connections + generate code */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setEditMode(v => !v)}
                    className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all cursor-pointer shrink-0 ${
                      editMode
                        ? 'bg-amber-100 text-amber-700 shadow-sm'
                        : 'bg-surface-container-high/70 text-on-surface-variant/70 hover:bg-surface-container-high hover:text-on-surface'
                    }`}
                    title={editMode ? t('Exit edit mode') : t('Edit connections')}
                  >
                    <Pencil size={11} />
                    <span>{t('Connections')}</span>
                  </button>
                  {sessionRunId && (
                    <button
                      onClick={generateCode}
                      disabled={generatingCode}
                      className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all cursor-pointer shrink-0 ${
                        generatingCode
                          ? 'bg-surface-container-high/70 text-on-surface-variant/30'
                          : 'bg-surface-container-high/70 text-on-surface-variant/70 hover:bg-surface-container-high hover:text-on-surface'
                      }`}
                      title="Generate React code"
                    >
                      <Code size={11} />
                      <span>{t('Code')}</span>
                    </button>
                  )}
                </div>

                {/* Separator */}
                <div className="w-px h-4 bg-outline/25 shrink-0" />

                {/* Device Mode Selector */}
                <div className="flex bg-surface-container p-0.5 rounded-lg border border-outline/40 text-[10px]">
                  <button
                    onClick={() => setDeviceMode('desktop')}
                    className={`px-2.5 py-1 rounded transition-all cursor-pointer font-semibold ${
                      deviceMode === 'desktop' ? 'bg-surface-bright text-on-surface shadow-2xs' : 'text-on-surface-variant'
                    }`}
                  >
                    Desktop
                  </button>
                  <button
                    onClick={() => setDeviceMode('tablet')}
                    className={`px-2.5 py-1 rounded transition-all cursor-pointer font-semibold ${
                      deviceMode === 'tablet' ? 'bg-surface-bright text-on-surface shadow-2xs' : 'text-on-surface-variant'
                    }`}
                  >
                    Tablet
                  </button>
                  <button
                    onClick={() => setDeviceMode('mobile')}
                    className={`px-2.5 py-1 rounded transition-all cursor-pointer font-semibold ${
                      deviceMode === 'mobile' ? 'bg-surface-bright text-on-surface shadow-2xs' : 'text-on-surface-variant'
                    }`}
                  >
                    Mobile
                  </button>
                </div>
              </div>
              
              {/* Viewport Frame (Dynamically scaled to fill maximum container area) */}
              <div className="flex-1 bg-surface-container-low flex items-center justify-center p-4 overflow-hidden relative min-h-[380px]">
                {activeScreen?.html ? (
                  <div className="flex flex-col items-center">
                    <div 
                      className={`shadow-md bg-white overflow-hidden relative transition-all duration-300 ${
                        deviceMode === 'mobile'
                          ? 'border-[6px] border-neutral-900 rounded-[28px] shadow-lg'
                          : deviceMode === 'tablet'
                          ? 'border-[5px] border-neutral-800 rounded-[20px] shadow-md'
                          : 'border-[6px] border-neutral-850 rounded-lg shadow-md bg-neutral-850'
                      }`}
                      style={{
                        width: `${cardWidth + (deviceMode === 'mobile' ? 12 : deviceMode === 'tablet' ? 10 : 12)}px`,
                        height: `${cardHeight + (deviceMode === 'mobile' ? 12 : deviceMode === 'tablet' ? 10 : 12)}px`,
                      }}
                    >
                      {deviceMode === 'mobile' && (
                        /* Phone Camera Notch */
                        <div className="absolute top-1 left-1/2 -translate-x-1/2 w-12 h-3.5 bg-neutral-900 rounded-full z-20" />
                      )}
                      <div className="w-full h-full overflow-hidden relative rounded-md bg-white">
                        <iframe key={activeScreenId}
                          ref={iframeRef}
                          title={`simulator-iframe-${deviceMode}`}
                          srcDoc={buildSimulatorSrcDoc(activeScreen.html)}
                          className="border-none absolute top-0 left-0"
                          style={{
                            width: `${simWidth}px`,
                            height: `${simHeight}px`,
                            transform: `scale(${scale})`,
                            transformOrigin: 'top left',
                            transition: 'transform 0.3s ease'
                          }}
                          sandbox="allow-scripts allow-same-origin"
                          onLoad={(e) => { applyStateToIframe(e.currentTarget); injectPrototypeClickHandlers(e.currentTarget); }}
                        />
                      </div>
                    </div>
                    {/* Render stand and base only in Desktop mode for computer monitor visualization */}
                    {deviceMode === 'desktop' && (
                      <>
                        <div className="w-8 h-3.5 bg-neutral-700/80 shadow-2xs shrink-0" />
                        <div className="w-20 h-1 bg-neutral-600 rounded-full shadow-2xs -mt-0.5 shrink-0" />
                      </>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-on-surface-variant/50 italic">{t('This screen has no HTML content')}</div>
                )}
              </div>

              {/* SVG Connection Lines Overlay (edit mode only) */}
              {editMode && (
                <div ref={linesContainerRef} className="absolute inset-0 z-30" style={{margin:0,padding:0,pointerEvents:dragLine?'auto':'none'}}
                  onMouseMove={dragLine ? (e) => {
                    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                    setDragLine(prev => prev ? {...prev, mouseX: e.clientX - rect.left, mouseY: e.clientY - rect.top} : null);
                    // Auto-scroll sidebar when dragging near edges
                    const sidebar = sidebarScrollRef.current;
                    if (sidebar) {
                      const sr = sidebar.getBoundingClientRect();
                      const edgeZone = 60;
                      const maxSpeed = 12;
                      const dy = e.clientY - sr.top;
                      if (dy < edgeZone) {
                        sidebar.scrollTop -= Math.round(maxSpeed * (1 - dy / edgeZone));
                      } else if (dy > sr.height - edgeZone) {
                        sidebar.scrollTop += Math.round(maxSpeed * (1 - (sr.height - dy) / edgeZone));
                      }
                    }
                  } : undefined}
                  onMouseUp={dragLine ? (e) => {
                    // Hit-test thumbnails
                    const target = document.elementsFromPoint(e.clientX, e.clientY).find(el => el.getAttribute('data-screen-id'));
                    if (target) {
                      const targetId = target.getAttribute('data-screen-id')!;
                      if (dragLine!.existingFlow) {
                        // Reconnect: update existing flow's target
                        setMutableFlows(prev => prev.map(f =>
                          (f.from === dragLine!.existingFlow.from && f.to === dragLine!.existingFlow.to && f.source_element_text === dragLine!.existingFlow.source_element_text)
                            ? {...f, to: targetId, reason: '用户重新连线'}
                            : f
                        ));
                      } else {
                        // Create new flow
                        setMutableFlows(prev => [...prev, {
                          from: activeScreenId, to: targetId, trigger: 'click',
                          confidence: 1.0, reason: '用户手动连线',
                          source_element_text: dragLine!.sourceElementText.trim(),
                          source_element_role: 'Unknown', params: {}, status: 'approved',
                        }]);
                      }
                    }
                    setDragLine(null);
                  } : undefined}
                >
                  <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{overflow:'visible'}}>
                    {connectionLines.map((line, i) => (
                      <g key={i} className="group">
                        <line
                          x1={line.fromX} y1={line.fromY} x2={line.toX} y2={line.toY}
                          stroke="rgba(59,130,246,0.5)" strokeWidth="1.5" strokeDasharray="4 2"
                          className="pointer-events-none"
                        />
                        <circle cx={line.fromX} cy={line.fromY} r="4" fill="#3b82f6" className="pointer-events-none" />
                        {/* Target circle — draggable to reconnect */}
                        {/* Target endpoint — arrow if offscreen, circle if visible */}
                        {(line as any).offscreen ? (
                          <polygon
                            points={`${line.toX - 5},${line.toY - 5} ${line.toX + 5},${line.toY} ${line.toX - 5},${line.toY + 5}`}
                            fill="#3b82f6"
                            className="pointer-events-none"
                          />
                        ) : (
                          <circle cx={line.toX} cy={line.toY} r="6" fill="#3b82f6" className="cursor-grab active:cursor-grabbing pointer-events-auto"
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              setDragLine({
                                fromX: line.fromX, fromY: line.fromY,
                                mouseX: line.toX, mouseY: line.toY,
                                sourceElementText: line.flow.source_element_text || '',
                                existingFlow: line.flow,
                              });
                            }}
                          />
                        )}
                        {/* Delete button near midpoint */}
                        <g
                          onClick={() => {
                            setMutableFlows(prev => prev.filter(f =>
                              !(f.from === line.flow.from && f.to === line.flow.to && f.source_element_text === line.flow.source_element_text)
                            ));
                          }}
                          className="cursor-pointer pointer-events-auto"
                        >
                          <circle
                            cx={(line.fromX + line.toX) / 2}
                            cy={(line.fromY + line.toY) / 2}
                            r="8" fill="white" stroke="rgba(239,68,68,0.6)" strokeWidth="1"
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                          />
                          <text
                            x={(line.fromX + line.toX) / 2}
                            y={(line.fromY + line.toY) / 2 + 3}
                            textAnchor="middle" fontSize="8" fill="#ef4444"
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                          >✕</text>
                        </g>
                      </g>
                    ))}
                    {/* Drag line preview */}
                    {dragLine && (
                      <line
                        x1={dragLine.fromX} y1={dragLine.fromY}
                        x2={dragLine.mouseX} y2={dragLine.mouseY}
                        stroke="#3b82f6" strokeWidth="2" strokeDasharray="6 3"
                        className="pointer-events-none"
                      />
                    )}
                  </svg>
                </div>
              )}
              
              
            </div>
          </div>
        )}

        {activeTab === 'matrix' && (
          <div className="bg-surface-bright p-6 rounded-2xl border border-outline/35 shadow-xs">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-4">
              {t('Multi-Viewport Matrix')}
            </h4>
            {activeScreen?.html ? (
              <MatrixPreview activeScreenHtml={activeScreen.html} state={state} extreme={extreme} />
            ) : (
              <div className="text-xs text-on-surface-variant/50 italic">{t('This screen has no HTML content')}</div>
            )}
          </div>
        )}

        {activeTab === 'flows' && (
          <div className="bg-surface-bright p-6 rounded-2xl border border-outline/35 shadow-xs select-none">
            <h4 className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-4 flex items-center gap-2">
              <Activity size={12} className="text-primary" />
              {t('Logic Connections Chart')}
            </h4>
            
            {mutableFlows.length === 0 ? (
              <div className="text-center py-8">
                <HelpCircle size={32} className="text-on-surface-variant/30 mx-auto mb-2" />
                <p className="text-xs text-on-surface-variant/50 italic">{t('No page navigation links could be inferred from current screens')}</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[360px] overflow-auto pr-2">
                {mutableFlows.map((f: any, idx: number) => {
                  const fromScreen = screens.find(s => s.id === f.from);
                  const toScreen = screens.find(s => s.id === f.to);
                  return (
                    <div key={idx} className="p-3 bg-surface border border-outline/30 rounded-xl flex items-center justify-between text-xs gap-4 hover:border-primary/30 transition-colors">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-on-surface px-2 py-0.5 bg-surface-container rounded">{fromScreen?.name || f.from}</span>
                        <span className="text-on-surface-variant/50">⟶</span>
                        <span className="font-semibold text-primary px-2 py-0.5 bg-primary/5 rounded">{toScreen?.name || f.to}</span>
                      </div>
                      <div className="flex items-center gap-1 text-[10px] text-on-surface-variant bg-surface-container-high/60 px-2 py-0.5 rounded-full font-medium">
                        <CheckCircle size={10} className="text-green-600" />
                        <span>规则: {f.reason}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Hot Zone Context Menu */}
      {contextMenu && (
        <div className="fixed inset-0 z-50" onClick={() => setContextMenu(null)}>
          <div
            ref={contextMenuRef}
            className="absolute bg-surface border border-outline/50 rounded-xl shadow-lg p-1.5 min-w-[170px] max-h-[320px] overflow-y-auto"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-on-surface-variant/50 mb-0.5">
              {t('Hotspot')}: {contextMenu.elementText}
            </div>
            {contextMenu.flow ? (
              <>
                <button
                  onClick={() => { navigateTo(contextMenu.flow!.to); setContextMenu(null); }}
                  className="w-full text-left px-2 py-1.5 text-[10px] rounded-md hover:bg-primary/10 text-primary font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
                >
                  <ArrowRight size={10} />
                  {t('Go to')} {screens.find(s => s.id === contextMenu.flow!.to)?.name || contextMenu.flow!.to}
                </button>
                <div className="border-t border-outline/20 my-1" />
                <div className="px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-on-surface-variant/40">
                  {t('Change target page')}
                </div>
                {screens.filter(s => s.id !== activeScreenId).slice(0, 6).map(s => (
                  <button
                    key={s.id}
                    onClick={() => { editFlowTarget(contextMenu.flow!, s.id); navigateTo(s.id); }}
                    className={`w-full text-left px-2 py-1 text-[10px] rounded-md transition-colors cursor-pointer ${
                      contextMenu.flow!.to === s.id
                        ? 'bg-primary/10 text-primary font-semibold'
                        : 'hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface'
                    }`}
                  >
                    {s.name || s.id} {contextMenu.flow!.to === s.id && '✓'}
                  </button>
                ))}
                <div className="border-t border-outline/20 my-1" />
                <button
                  onClick={() => deleteFlow(contextMenu.flow!)}
                  className="w-full text-left px-2 py-1.5 text-[10px] rounded-md hover:bg-red-50 text-red-500 transition-colors cursor-pointer flex items-center gap-1.5"
                >
                  <X size={10} />
                  {t('Delete this interaction')}
                </button>
              </>
            ) : (
              <div className="space-y-0.5">
                <div className="px-1.5 py-0.5 text-[8px] uppercase tracking-wider text-on-surface-variant/40">
                  {t('New interaction → Select target')}
                </div>
                {screens.filter(s => s.id !== activeScreenId).slice(0, 6).map(s => (
                  <button
                    key={s.id}
                    onClick={() => { addFlowForElement(contextMenu.elementText, s.id); navigateTo(s.id); }}
                    className="w-full text-left px-2 py-1 text-[10px] rounded-md hover:bg-primary/10 text-on-surface hover:text-primary transition-colors cursor-pointer"
                  >
                    → {s.name || s.id}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Code Generation Result Modal */}
      {codeGenResult && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30" onClick={() => setCodeGenResult(null)}>
          <div className="bg-surface border border-outline/40 rounded-2xl shadow-xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-on-surface">
                {t('Code Generated')}
              </h3>
              <button onClick={() => setCodeGenResult(null)} className="p-1 rounded-md hover:bg-surface-container-high text-on-surface-variant/60 cursor-pointer">
                <X size={15} />
              </button>
            </div>
            <p className="text-xs text-on-surface-variant/70 text-center mb-4 leading-relaxed">
              {codeGenResult.written} files written to ./generated/. Copy the prompt below and paste it to an AI coding agent to integrate the components.
            </p>
            <div className="flex gap-2">
              <button
                onClick={copyPath}
                className="flex-1 text-center px-2 py-1.5 text-[10px] font-semibold rounded-lg border border-outline/40 text-on-surface-variant hover:bg-surface-container-high transition-colors cursor-pointer"
              >
                {pathCopied ? 'Copied' : 'Copy Path'}
              </button>
              <button
                onClick={async () => {
                  await navigator.clipboard.writeText(aiPrompt);
                  setCopyingPrompt(true);
                  setTimeout(() => setCopyingPrompt(false), 1500);
                }}
                className="flex-1 text-center px-2 py-1.5 text-[10px] font-semibold rounded-lg bg-on-surface text-surface hover:bg-on-surface/90 transition-colors cursor-pointer"
              >
                {copyingPrompt ? 'Copied' : 'Copy Prompt'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Developer Debug Panel */}
      {payload && (
        <details className="bg-surface border-t border-outline/40 px-6 py-3 text-xs text-on-surface-variant shrink-0">
          <summary className="cursor-pointer hover:text-on-surface select-none font-semibold text-[11px]">
            {t('Developer Debug JSON')}
          </summary>
          <pre className="mt-2 p-3 bg-surface-container rounded-xl border border-outline/30 text-[10px] overflow-auto max-h-40 font-mono text-on-surface-variant">
            {JSON.stringify(payload, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
