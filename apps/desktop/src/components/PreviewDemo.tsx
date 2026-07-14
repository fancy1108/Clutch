import React, { useEffect, useState, useRef } from 'react';
import { Layers, Tv, Activity, HelpCircle, CheckCircle, ChevronDown } from 'lucide-react';
import StateController from './StateController';
import MatrixPreview from './MatrixPreview';
import { DesignScreen } from '../services/designApi';
import { useLanguage } from './LanguageContext';

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
      setActiveScreenId(screens[0].id);
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

    fetch('/api/preview/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
      .then((r) => r.json())
      .then((data) => {
        setPayload(data);
        setLoading(false);
      })
      .catch((e) => {
        setPayload({ error: String(e) });
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

  // Re-trigger DOM style applications when react states shift
  useEffect(() => {
    if (iframeRef.current) {
      applyStateToIframe(iframeRef.current);
    }
  }, [state, extreme, activeScreenId]);

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
  const activeFlows = payload?.flows?.filter((f: any) => f.from === activeScreenId) || [];

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
            {t('Logic Connections Chart')} ({payload?.flows?.length || 0})
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
                            onClick={() => {
                              setActiveScreenId(s.id);
                              setIsScreenDropdownOpen(false);
                            }}
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

              <div className="flex-1 overflow-auto">
                <label className="block text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-2.5">
                  {t('Page Transition Links')} ({activeFlows.length})
                </label>
                {activeFlows.length === 0 ? (
                  <p className="text-xs text-on-surface-variant/50 italic px-1">{t('No outbound flows inferred for this screen')}</p>
                ) : (
                  <div className="space-y-2">
                    {activeFlows.map((f: any, idx: number) => {
                      const targetScreen = screens.find((s) => s.id === f.to);
                      return (
                        <button
                          key={idx}
                          onClick={() => setActiveScreenId(f.to)}
                          className="w-full text-left p-2.5 rounded-xl border border-outline/30 bg-surface-container-low hover:border-primary/40 hover:bg-surface-bright transition-all text-xs flex flex-col gap-1 text-on-surface hover:text-primary group cursor-pointer"
                        >
                          <span className="font-semibold text-primary group-hover:underline">
                            {t('Transition to:')} {targetScreen?.name || f.to}
                          </span>
                          <span className="text-[10px] text-on-surface-variant/60 font-medium">
                            {t('Inference Rule:')} {f.reason}
                          </span>
                        </button>
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
                <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                  {t('Live Screen Preview')}: {activeScreen?.name}
                </span>
                
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
                        <iframe
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
                          onLoad={(e) => applyStateToIframe(e.currentTarget)}
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
