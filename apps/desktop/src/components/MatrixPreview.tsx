import React, { useEffect, useState, useRef } from 'react';

interface MatrixPreviewProps {
  activeScreenHtml: string;
  state: string;
  extreme: boolean;
}

export default function MatrixPreview({ activeScreenHtml, state, extreme }: MatrixPreviewProps) {
  const [diagnostics, setDiagnostics] = useState<Record<string, string[]>>({});

  const iframe1440Ref = useRef<HTMLIFrameElement>(null);
  const iframe1024Ref = useRef<HTMLIFrameElement>(null);
  const iframe390Ref = useRef<HTMLIFrameElement>(null);

  // Apply state modifications directly to the iframe window objects
  const applyStateToIframe = (iframe: HTMLIFrameElement, vp: string) => {
    try {
      const doc = iframe.contentDocument || iframe.contentWindow?.document;
      if (!doc || !doc.body) return;

      // 1. Clear old banners
      const oldBanners = doc.querySelectorAll('.clutch-preview-banner');
      oldBanners.forEach(b => b.remove());

      // 2. Restore original inputs styling
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

      // 7. Auto Diagnostics Scan
      const scan = () => {
        try {
          const issues: string[] = [];
          if (doc.documentElement.scrollWidth > iframe.contentWindow!.innerWidth + 2) {
            issues.push('页面横向滚动溢出');
          }
          const elements = doc.querySelectorAll('h1, h2, h3, h4, p, span, button, a, div');
          elements.forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > iframe.contentWindow!.innerWidth + 2) {
              const name = el.tagName + (el.className ? '.' + el.className.split(' ')[0] : '');
              issues.push('元素 ' + name + ' 超出视口');
            }
            if (el.scrollWidth > el.clientWidth + 2 && (el as HTMLElement).style.overflow !== 'auto' && (el as HTMLElement).style.overflow !== 'scroll') {
              const name = el.tagName + (el.className ? '.' + el.className.split(' ')[0] : '');
              issues.push('内容溢出截断: ' + name);
            }
          });
          const uniqueIssues = [...new Set(issues)].slice(0, 3);
          window.postMessage({ __preview_diag: true, vp: vp, issues: uniqueIssues }, '*');
        } catch (err) {
          /* Ignore viewport read boundaries errors */
        }
      };
      setTimeout(scan, 250);
    } catch (e) {
      /* Handle iframe lifecycle load catches */
    }
  };

  // Re-trigger styles application on state changes
  useEffect(() => {
    if (iframe1440Ref.current) applyStateToIframe(iframe1440Ref.current, '1440');
    if (iframe1024Ref.current) applyStateToIframe(iframe1024Ref.current, '1024');
    if (iframe390Ref.current) applyStateToIframe(iframe390Ref.current, '390');
  }, [state, extreme, activeScreenHtml]);

  const viewports = ['1440', '1024', '390'];

  function buildViewportSrcDoc() {
    if (!activeScreenHtml) return '';

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
        div, form, section, main, header, footer {
          max-width: 100% !important;
        }
        img, svg {
          max-width: 100% !important;
          height: auto !important;
        }
      </style>
    `;

    let html = activeScreenHtml;
    if (html.includes('</head>')) {
      return html.replace('</head>', `${adapterStyle}</head>`);
    }
    return adapterStyle + html;
  }

  return (
    <div className="flex gap-4 flex-wrap select-none text-left items-start justify-center">
      <div className="flex-[3] flex gap-5 flex-wrap items-end justify-center py-2">
        {/* Desktop Device (1440px) */}
        <div className="flex flex-col items-center gap-1.5 font-sans">
          <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/80">Desktop (1440px)</div>
          <div className="relative border-[5px] border-neutral-800 rounded-t-xl shadow-md bg-neutral-800 overflow-hidden w-[240px] h-[150px] flex items-center justify-center">
            <div className="w-[230px] h-[140px] overflow-hidden rounded-sm bg-white relative">
              <iframe
                ref={iframe1440Ref}
                title="preview-1440"
                srcDoc={buildViewportSrcDoc()}
                className="border-none absolute top-0 left-0"
                style={{
                  width: '1440px',
                  height: `${Math.round(140 / (230 / 1440))}px`,
                  transform: `scale(${230 / 1440})`,
                  transformOrigin: 'top left',
                }}
                sandbox="allow-scripts allow-same-origin"
                onLoad={(e) => applyStateToIframe(e.currentTarget, '1440')}
              />
            </div>
          </div>
          <div className="w-[260px] h-1.5 bg-neutral-700 rounded-b-xl shadow-sm -mt-0.5" />
        </div>

        {/* Tablet Device (1024px) */}
        <div className="flex flex-col items-center gap-1.5 font-sans">
          <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/80">Tablet (1024px)</div>
          <div className="relative border-[6px] border-neutral-800 rounded-[20px] shadow-md bg-neutral-800 p-0.5 overflow-hidden w-[180px] h-[240px] flex items-center justify-center">
            <div className="w-[168px] h-[228px] overflow-hidden rounded-[14px] bg-white relative">
              <iframe
                ref={iframe1024Ref}
                title="preview-1024"
                srcDoc={buildViewportSrcDoc()}
                className="border-none absolute top-0 left-0"
                style={{
                  width: '1024px',
                  height: `${Math.round(228 / (168 / 1024))}px`,
                  transform: `scale(${168 / 1024})`,
                  transformOrigin: 'top left',
                }}
                sandbox="allow-scripts allow-same-origin"
                onLoad={(e) => applyStateToIframe(e.currentTarget, '1024')}
              />
            </div>
          </div>
        </div>

        {/* Mobile Device (390px) */}
        <div className="flex flex-col items-center gap-1.5 font-sans">
          <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/80">Mobile (390px)</div>
          <div className="relative border-[6px] border-neutral-900 rounded-[24px] shadow-lg bg-neutral-900 p-0.5 overflow-hidden w-[180px] h-[280px] flex items-center justify-center">
            {/* Camera notch */}
            <div className="absolute top-1.5 left-1/2 -translate-x-1/2 w-10 h-3 bg-neutral-900 rounded-full z-20" />
            <div className="w-[168px] h-[268px] overflow-hidden rounded-[18px] bg-white relative">
              <iframe
                ref={iframe390Ref}
                title="preview-390"
                srcDoc={buildViewportSrcDoc()}
                className="border-none absolute top-0 left-0"
                style={{
                  width: '390px',
                  height: `${Math.round(268 / (168 / 390))}px`,
                  transform: `scale(${168 / 390})`,
                  transformOrigin: 'top left',
                }}
                sandbox="allow-scripts allow-same-origin"
                onLoad={(e) => applyStateToIframe(e.currentTarget, '390')}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Diagnostics List */}
      <div className="flex-1 min-w-[180px] p-2 border-l border-outline/40 self-stretch font-sans">
        <div className="text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2">布局适配诊断</div>
        {viewports.map((vp) => (
          <div key={vp} className="mb-2.5 text-[11px]">
            <div className="font-bold text-on-surface-variant">{vp}px</div>
            {diagnostics[vp] && diagnostics[vp].length ? (
              <ul className="pl-4 my-1 text-rose-750 list-disc">
                {diagnostics[vp].map((m, i) => (
                  <li key={i} className="mb-1 leading-normal">{m}</li>
                ))}
              </ul>
            ) : (
              <div className="text-green-600 text-[10px] mt-0.5 font-medium">✓ 适配正常</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
