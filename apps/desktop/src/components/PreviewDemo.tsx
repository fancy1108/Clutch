import React, { useEffect, useState, useRef } from 'react';
import { Layers, Tv, Activity, HelpCircle, CheckCircle, ChevronDown, ArrowLeft, ArrowRight, X, Plus } from 'lucide-react';
import StateController from './StateController';
import MatrixPreview from './MatrixPreview';
import { DesignScreen } from '../services/designApi';
import { useLanguage } from './LanguageContext';
import { sidecarFetch, sidecarHttpUrl } from '../services/sidecarUrl';

interface PreviewDemoProps {
  screens: DesignScreen[];
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

export default function PreviewDemo({ screens }: PreviewDemoProps) {
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
  const [isAddingFlow, setIsAddingFlow] = useState(false);
  const [newFlowTarget, setNewFlowTarget] = useState('');
  const [newFlowSourceText, setNewFlowSourceText] = useState('');
  const mutableFlowsRef = useRef<any[]>([]);

  // Keep ref in sync so click-time lookups always use latest flows
  useEffect(() => { mutableFlowsRef.current = mutableFlows; }, [mutableFlows]);

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

  // Close screen dropdown on click outside
  useEffect(() => {
    function clickOutside(e: MouseEvent) {
      if (screenDropdownRef.current && !screenDropdownRef.current.contains(e.target as Node)) {
        setIsScreenDropdownOpen(false);
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
        setMutableFlows(data.flows || []);
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
          banner.innerHTML = '<span>⚠️</span> <span>连接较慢，输入可能延迟提交 (Slow connection warning)</span>';
        } else if (metrics.length > 0) {
          banner.innerHTML = '<span>⚠️</span> <span>部分数据指标同步延迟 (Metrics sync warning)</span>';
        } else {
          banner.innerHTML = '<span>⚠️</span> <span>当前业务数据加载较慢 (Slow response warning)</span>';
        }
        container.insertBefore(banner, container.firstChild);
      } else if (state === 'Critical') {
        const banner = doc.createElement('div');
        banner.className = 'clutch-preview-banner';
        banner.style.cssText = 'background:#fff1f2; border:1px solid #f43f5e; padding:8px 12px; border-radius:8px; margin-bottom:12px; font-size:10px; color:#b91c1c; font-weight:500; display:flex; align-items:center; gap:6px; box-shadow:0 1px 2px rgba(0,0,0,0.05);';
        if (inputs.length > 0) {
          banner.innerHTML = '<span>❌</span> <span>用户名或密码验证错误，请重试 (Verification failed)</span>';
          inputs.forEach(input => {
            (input as HTMLElement).style.borderColor = '#f43f5e';
            (input as HTMLElement).style.boxShadow = '0 0 0 1px #f43f5e';
          });
        } else if (metrics.length > 0) {
          banner.innerHTML = '<span>❌</span> <span>数据库连接超时，服务暂时不可用 (Database Timeout 500)</span>';
        } else {
          banner.innerHTML = '<span>❌</span> <span>权限验证失败，会话已过期 (Unauthorized 401)</span>';
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

      // 0) Clear previous clickable state so delete/add take effect immediately
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

      const otherScreens = screens.filter(s => s.id !== activeScreenId);
      const fallbackTarget = otherScreens.length > 0 ? otherScreens[0].id : null;

      let injected = 0;
      const sel = 'button, a, [role="button"], input[type="submit"], input[type="button"]';
      doc.querySelectorAll(sel).forEach((el) => {
        const rawText = (el.textContent || (el as HTMLInputElement).value || '').trim();
        if (!rawText) return;
        let targetId: string | null = null;
        const rawLower = rawText.toLowerCase();
        if (flowByText.has(rawLower)) {
          targetId = flowByText.get(rawLower)!;
        } else {
          for (const [ft, tid] of flowByText) {
            if (rawLower.includes(ft) || ft.includes(rawLower)) { targetId = tid; break; }
          }
        }
        if (!targetId && fallbackTarget) {
          const preferred = otherScreens.find(s => {
            const name = (s.name || '').toLowerCase();
            const kw = ['dashboard','home','main','index','overview'];
            return kw.some(k => name.includes(k));
          });
          targetId = preferred ? preferred.id : fallbackTarget;
        }
        if (targetId) {
          const htmlEl = el as HTMLElement;
          htmlEl.setAttribute('data-clutch-clickable', targetId);
          htmlEl.style.cursor = 'pointer';
          htmlEl.style.outline = '2px solid rgba(59,130,246,0.3)';
          htmlEl.style.outlineOffset = '2px';
          const tgtName = screens.find(s => s.id === targetId)?.name || targetId;
          htmlEl.title = `Click to navigate to ${tgtName}`;
          // onclick (not addEventListener) so clearing/re-running overwrites, never stacks
          htmlEl.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Re-lookup from latest flows at click time (handles delete)
            const cur = mutableFlowsRef.current.filter((f: any) => f.from === activeScreenId);
            const m = cur.find((f: any) =>
              (f.source_element_text || '').toLowerCase().trim() === rawLower ||
              rawLower.includes((f.source_element_text || '').toLowerCase()) ||
              (f.source_element_text || '').toLowerCase().includes(rawLower)
            );
            if (m) navigateTo(m.to);
          };
          injected++;
        }
      });
      setClickableCount(injected);
    } catch (_) { setClickableCount(0); }
  }, [mutableFlows, activeScreenId, navigateTo, screens]);

  // Re-trigger DOM style applications and click injection when react states shift
  useEffect(() => {
    if (iframeRef.current) {
      applyStateToIframe(iframeRef.current);
      injectPrototypeClickHandlers(iframeRef.current);
    }
  }, [state, extreme, activeScreenId, injectPrototypeClickHandlers]);

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

  const deleteFlow = (flowIndex: number) => {
    // Find the actual index in mutableFlows (not just activeFlows)
    const flow = activeFlows[flowIndex];
    setMutableFlows(prev => prev.filter(f => !(f.from === flow.from && f.to === flow.to)));
  };

  const addFlow = (targetId: string) => {
    if (!targetId || targetId === activeScreenId || !newFlowSourceText.trim()) return;
    const newFlow = {
      from: activeScreenId,
      to: targetId,
      trigger: 'click',
      confidence: 1.0,
      reason: '用户手动添加的连线',
      source_element_text: newFlowSourceText.trim(),
      source_element_role: 'Unknown',
      params: {},
      status: 'approved',
    };
    setMutableFlows(prev => [...prev, newFlow]);
    setIsAddingFlow(false);
    setNewFlowTarget('');
    setNewFlowSourceText('');
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
              {/* Unified Dropdown Selector */}
              <div className="relative">
                <label className="block text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2 select-none">
                  {t('Select Screen Page')}
                </label>
                
                <div className="relative" ref={screenDropdownRef}>
                  <button
                    type="button"
                    onClick={() => setIsScreenDropdownOpen(!isScreenDropdownOpen)}
                    className="bg-surface border border-outline/40 hover:border-outline-variant/60 rounded-lg px-3 py-1.5 text-xs text-on-surface flex items-center justify-between gap-2.5 cursor-pointer font-semibold shadow-2xs select-none w-full"
                  >
                    <span>{activeScreen?.name || activeScreenId}</span>
                    <ChevronDown size={12} className={`text-on-surface-variant/60 transition-transform duration-200 ${isScreenDropdownOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {isScreenDropdownOpen && (
                    <div className="absolute left-0 top-full mt-1 z-30 bg-surface border border-outline rounded-lg shadow-md py-1 overflow-hidden w-full max-h-48 overflow-y-auto">
                      {screens.map((s) => {
                        const isActive = s.id === activeScreenId;
                        return (
                          <button
                            key={s.id}
                            type="button"
                            onClick={() => navigateTo(s.id)}
                            className={`w-full text-left px-3 py-2 text-xs flex items-center gap-1.5 cursor-pointer transition-colors font-medium ${
                              isActive
                                ? 'bg-surface-container text-on-surface font-semibold'
                                : 'text-on-surface-variant/80 hover:text-on-surface hover:bg-surface-container-high/40'
                            }`}
                          >
                            {s.name || s.id}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* Page Transition Links */}
              <div className="flex-1 overflow-auto">
                <div className="flex items-center justify-between mb-2.5">
                  <label className="block text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                    {t('Page Transition Links')} ({activeFlows.length})
                  </label>
                  <button
                    onClick={() => { setIsAddingFlow(true); setNewFlowTarget(''); setNewFlowSourceText(''); }}
                    className="p-0.5 rounded hover:bg-surface-container-high transition-colors text-on-surface-variant/60 hover:text-primary cursor-pointer"
                    title="手动添加连线"
                  >
                    <Plus size={12} />
                  </button>
                </div>

                {/* Add Flow Form */}
                {isAddingFlow && (
                  <div className="mb-2 p-2.5 bg-surface-container-low rounded-xl border border-outline/30 space-y-2">
                    <label className="block text-[9px] font-bold uppercase tracking-wider text-on-surface-variant/70">
                      触发元素文本
                    </label>
                    <input
                      type="text"
                      value={newFlowSourceText}
                      onChange={(e) => setNewFlowSourceText(e.target.value)}
                      placeholder="输入按钮文字，如「登录」「Go to Settings」…"
                      className="w-full text-[10px] bg-surface border border-outline/40 rounded-lg px-2.5 py-1.5 text-on-surface placeholder:text-on-surface-variant/30 focus:outline-none focus:border-primary/60 transition-colors"
                    />
                    <label className="block text-[9px] font-bold uppercase tracking-wider text-on-surface-variant/70">
                      目标页面
                    </label>
                    <div className="grid grid-cols-2 gap-1.5">
                      {screens.filter(s => s.id !== activeScreenId).map(s => (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => setNewFlowTarget(s.id)}
                          className={`text-left text-[10px] px-2.5 py-1.5 rounded-lg border transition-all font-medium cursor-pointer ${
                            newFlowTarget === s.id
                              ? 'bg-primary/10 border-primary/40 text-primary'
                              : 'bg-surface border-outline/30 text-on-surface-variant hover:border-outline/60 hover:text-on-surface'
                          }`}
                        >
                          {s.name || s.id}
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-1.5 pt-0.5">
                      <button
                        onClick={() => { addFlow(newFlowTarget); setNewFlowSourceText(''); }}
                        disabled={!newFlowTarget || !newFlowSourceText.trim()}
                        className="flex-1 text-[10px] bg-primary text-white rounded-lg px-2.5 py-1.5 font-semibold cursor-pointer disabled:opacity-30 transition-opacity"
                      >
                        确认添加
                      </button>
                      <button
                        onClick={() => { setIsAddingFlow(false); setNewFlowSourceText(''); }}
                        className="text-[10px] bg-surface-container-high text-on-surface-variant rounded-lg px-2.5 py-1.5 cursor-pointer hover:text-on-surface transition-colors"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                )}

                {activeFlows.length === 0 && !isAddingFlow ? (
                  <p className="text-xs text-on-surface-variant/50 italic px-1">{t('No outbound flows inferred for this screen')}</p>
                ) : (
                  <div className="space-y-2">
                    {activeFlows.map((f: any, idx: number) => {
                      const targetScreen = screens.find((s) => s.id === f.to);
                      const isManual = f.status === 'approved';
                      return (
                        <div
                          key={idx}
                          className="relative group"
                        >
                          <button
                            onClick={() => navigateTo(f.to)}
                            className="w-full text-left p-2.5 pr-7 rounded-xl border border-outline/30 bg-surface-container-low hover:border-primary/40 hover:bg-surface-bright transition-all text-xs flex flex-col gap-1 text-on-surface hover:text-primary cursor-pointer"
                          >
                            <span className="font-semibold text-primary group-hover:underline">
                              {isManual && '✏️ '}{t('Transition to:')} {targetScreen?.name || f.to}
                            </span>
                            <span className="text-[10px] text-on-surface-variant/60 font-medium">
                              {t('Inference Rule:')} {f.reason}
                            </span>
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); deleteFlow(idx); }}
                            className="absolute top-1.5 right-1.5 p-0.5 rounded-full hover:bg-red-100 text-on-surface-variant/30 hover:text-red-500 transition-all opacity-0 group-hover:opacity-100 cursor-pointer"
                            title="删除此连线"
                          >
                            <X size={11} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
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
                  {clickableCount > 0 && (
                    <span className="text-[9px] text-blue-500/70 font-medium ml-1 bg-blue-50 dark:bg-blue-950/40 px-1.5 py-0.5 rounded-full">
                      {clickableCount} 可点击
                    </span>
                  )}
                </div>
                
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
            
            {payload?.flows?.length === 0 ? (
              <div className="text-center py-8">
                <HelpCircle size={32} className="text-on-surface-variant/30 mx-auto mb-2" />
                <p className="text-xs text-on-surface-variant/50 italic">{t('No page navigation links could be inferred from current screens')}</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[360px] overflow-auto pr-2">
                {payload?.flows?.map((f: any, idx: number) => {
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
