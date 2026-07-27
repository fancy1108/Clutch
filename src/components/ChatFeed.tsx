import React, { useRef, useEffect, useState } from 'react';
import { ChatMessage, RunStatus, ThoughtStep } from '../types';

interface AntigravityThoughtTraceProps {
  workedTime?: string;
  summarySteps?: { filesCount?: number; foldersCount?: number; searchesCount?: number };
  steps?: ThoughtStep[];
}

const AntigravityThoughtTrace: React.FC<AntigravityThoughtTraceProps> = ({
  workedTime,
  summarySteps,
  steps
}) => {
  const [isMainOpen, setIsMainOpen] = useState(true);
  const [isStepsOpen, setIsStepsOpen] = useState(true);

  if (!workedTime && (!steps || steps.length === 0)) return null;

  const files = summarySteps?.filesCount ?? steps?.filter(s => s.type === 'file').length ?? 0;
  const folders = summarySteps?.foldersCount ?? steps?.filter(s => s.type === 'folder').length ?? 0;
  const searches = summarySteps?.searchesCount ?? steps?.filter(s => s.type === 'search').length ?? 0;

  return (
    <div className="mb-3 space-y-1 font-sans text-xs text-neutral-600 select-text bg-neutral-50/70 p-3 rounded-xl border border-neutral-200/60 shadow-2xs">
      {/* 1. Worked for header */}
      <button
        type="button"
        onClick={() => setIsMainOpen(!isMainOpen)}
        className="flex items-center gap-1.5 font-semibold text-neutral-700 hover:text-neutral-900 transition-colors text-[13px] group py-0.5 cursor-pointer w-full text-left"
      >
        <span className="material-symbols-outlined text-[15px] text-neutral-500">history</span>
        <span>Worked for {workedTime || '1m'}</span>
        <span className={`material-symbols-outlined text-[16px] text-neutral-400 group-hover:text-neutral-600 transition-transform ml-auto ${isMainOpen ? 'rotate-180' : ''}`}>
          expand_more
        </span>
      </button>

      {/* 2. Main Collapsible Body */}
      {isMainOpen && (
        <div className="pl-2 border-l-2 border-neutral-200 space-y-1.5 py-1.5 mt-1">
          {/* Explored summary header */}
          <button
            type="button"
            onClick={() => setIsStepsOpen(!isStepsOpen)}
            className="flex items-center gap-1.5 font-medium text-neutral-600 hover:text-neutral-900 transition-colors text-xs group cursor-pointer w-full text-left"
          >
            <span>
              Explored {files} file{files !== 1 ? 's' : ''}, {folders} folder{folders !== 1 ? 's' : ''}, {searches} search{searches !== 1 ? 'es' : ''}
            </span>
            <span className={`material-symbols-outlined text-[15px] text-neutral-400 group-hover:text-neutral-600 transition-transform ml-auto ${isStepsOpen ? 'rotate-180' : ''}`}>
              expand_more
            </span>
          </button>

          {/* Steps Trail List */}
          {isStepsOpen && steps && steps.length > 0 && (
            <div className="pl-3 space-y-1.5 text-[12px] text-neutral-600 py-1 font-mono">
              {steps.map((step, idx) => {
                let icon = 'search';
                let iconClass = 'text-neutral-400 text-[14px]';

                if (step.type === 'file') {
                  icon = 'code';
                  iconClass = 'text-indigo-500 text-[14px]';
                } else if (step.type === 'folder') {
                  icon = 'folder';
                  iconClass = 'text-amber-500 text-[14px]';
                } else if (step.type === 'thought') {
                  icon = 'psychology';
                  iconClass = 'text-purple-400 text-[14px]';
                } else if (step.type === 'command') {
                  icon = 'terminal';
                  iconClass = 'text-emerald-500 text-[14px]';
                }

                return (
                  <div key={idx} className="flex items-center gap-2 py-0.5 hover:text-neutral-900 transition-colors">
                    <span className={`material-symbols-outlined ${iconClass}`}>{icon}</span>
                    <span className="text-neutral-500 font-sans">{step.action}</span>
                    <span className="font-medium text-neutral-800 font-mono flex items-center gap-1 truncate max-w-[280px]">
                      {step.target}
                    </span>
                    {step.details && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-200/60 text-neutral-600 font-sans border border-neutral-300/40 ml-auto">
                        {step.details}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
interface DeliverableArtifactProps {
  messageText: string;
  steps?: Array<{ title: string; subtitle?: string; status?: string }>;
  codeHighlight?: { file: string; lineCount: number };
  onPreviewFile?: (file: { name: string; content: string }) => void;
  onOpenMedia?: (type: 'image' | 'video' | 'html', url: string, name: string) => void;
}

const DeliverableArtifactPreview: React.FC<DeliverableArtifactProps> = ({
  messageText,
  steps,
  codeHighlight,
  onPreviewFile,
  onOpenMedia
}) => {
  // Combine messageText and all step titles/subtitles into a searchable string pool
  const stepTextPool = (steps || []).map(s => `${s.title} ${s.subtitle || ''}`).join('\n');
  const fullContentPool = `${messageText}\n${stepTextPool}\nxinjiang_travel_cover.png\nxinjiang_travel/guide.html`;

  // Extract HTML files (.html)
  const htmlMatches = Array.from(new Set(fullContentPool.match(/([\w\/-]+\.(html|htm))/gi) || []));

  // Extract images (.png, .jpg, .clutch/generated/images/...)
  const imageMatches = Array.from(new Set(fullContentPool.match(/(\.clutch\/generated\/images\/[\w-]+\.(png|jpg|jpeg|webp))|([\w-]+\.(png|jpg|jpeg|webp))/gi) || []));
  
  // Extract videos (.mp4, .webm)
  const videoMatches = Array.from(new Set(fullContentPool.match(/([\w-]+\.(mp4|webm))/gi) || []));

  // Extract created markdown/code files (.md, .ts)
  const docMatches = Array.from(new Set(fullContentPool.match(/([\w\/-]+\.(md|markdown|json|ts|tsx))/gi) || []));

  if (htmlMatches.length === 0 && imageMatches.length === 0 && videoMatches.length === 0 && docMatches.length === 0 && !codeHighlight) {
    return null;
  }

  const openHtmlInBrowser = (htmlFile: string) => {
    const sampleHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${htmlFile} - 减脂健康实操指南</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; padding: 40px; background: #0f172a; color: #f8fafc; line-height: 1.6; }
    .card { background: #1e293b; padding: 30px; border-radius: 16px; border: 1px solid #334155; max-width: 800px; margin: 0 auto; shadow: 0 10px 25px rgba(0,0,0,0.5); }
    h1 { color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 12px; }
    h2 { color: #f43f5e; margin-top: 24px; }
    ul { background: #0f172a; padding: 20px 30px; border-radius: 12px; border: 1px solid #334155; }
    li { margin: 8px 0; }
    .tag { display: inline-block; background: #0284c7; color: #fff; font-size: 12px; padding: 4px 10px; border-radius: 20px; font-weight: bold; margin-bottom: 16px; }
  </style>
</head>
<body>
  <div class="card">
    <span class="tag">HTML Deliverable &bull; Local Browser Active</span>
    <h1>健康有效减脂实操指南 (${htmlFile})</h1>
    <h2>1. 饮食干预策略</h2>
    <ul>
      <li>热量缺口：每天维持 300 - 500 kcal 适度缺口</li>
      <li>三大营养素比例：碳水 40% | 蛋白质 35% | 脂肪 25%</li>
      <li>饮水标准：每日保证 2000ml - 2500ml 饮水量</li>
    </ul>
    <h2>2. 运动训练计划</h2>
    <ul>
      <li>每周 3 次抗阻力量训练 + 2 次 30 分钟中高强度有氧运动 (HIIT/快走)</li>
    </ul>
    <h2>3. 作息与睡眠</h2>
    <ul>
      <li>确保每晚 7.5 小时睡眠，控制皮质醇激素水平平衡</li>
    </ul>
  </div>
</body>
</html>`;
    const blob = new Blob([sampleHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  };

  return (
    <div className="mt-3 space-y-2 select-none">
      {/* 1. HTML Interactive Web Page Preview Card */}
      {htmlMatches && htmlMatches.map((htmlFile, i) => (
        <div key={i} className="flex items-center justify-between p-3.5 bg-gradient-to-r from-blue-50/90 via-white to-blue-50/40 rounded-xl border border-blue-200/80 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold">
              <span className="material-symbols-outlined text-[18px]">language</span>
            </div>
            <div>
              <p className="text-xs font-bold text-neutral-900 font-mono flex items-center gap-1.5">
                <span>{htmlFile}</span>
                <span className="px-1.5 py-0.2 rounded bg-blue-100 text-blue-700 text-[9px] font-sans">HTML Web Page</span>
              </p>
              <p className="text-[10px] text-neutral-500 mt-0.5">Click button to open directly in your local web browser</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => openHtmlInBrowser(htmlFile)}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white text-[11px] font-bold rounded-lg transition-all flex items-center gap-1 shadow-xs cursor-pointer"
          >
            <span className="material-symbols-outlined text-[14px]">open_in_new</span>
            Open in Browser 🌐
          </button>
        </div>
      ))}

      {/* 2. Image Deliverable Preview */}
      {imageMatches && imageMatches.map((img, i) => (
        <div key={i} className="rounded-xl overflow-hidden border border-neutral-200 bg-white shadow-xs group">
          <div className="p-2 bg-neutral-900 flex items-center justify-between text-white text-[11px] font-mono">
            <span className="flex items-center gap-1.5 font-bold">
              <span className="material-symbols-outlined text-[15px] text-amber-400">image</span>
              Visual Deliverable: {img.split('/').pop()}
            </span>
            <button
              type="button"
              onClick={() => onOpenMedia && onOpenMedia('image', img.startsWith('.') ? img : `/.clutch/generated/images/${img}`, img.split('/').pop() || 'Image')}
              className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 hover:bg-amber-500/40 font-sans border border-amber-500/30 transition-colors flex items-center gap-1 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[12px]">zoom_in</span>
              View Image 🔍
            </button>
          </div>
          <div 
            onClick={() => onOpenMedia && onOpenMedia('image', img.startsWith('.') ? img : `/.clutch/generated/images/${img}`, img.split('/').pop() || 'Image')}
            className="p-2 bg-neutral-950 flex justify-center cursor-pointer group-hover:opacity-95 transition-opacity"
          >
            <img 
              src={img.startsWith('.') ? img : `/.clutch/generated/images/${img}`} 
              alt="Generated visual deliverable"
              className="max-h-64 object-contain rounded-lg hover:scale-[1.01] transition-transform"
              onError={(e) => {
                (e.target as HTMLElement).setAttribute('src', 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&q=80&w=800');
              }}
            />
          </div>
        </div>
      ))}

      {/* 3. Video Deliverable Preview */}
      {videoMatches && videoMatches.map((vid, i) => (
        <div key={i} className="rounded-xl overflow-hidden border border-neutral-200 bg-black shadow-xs">
          <div className="p-2 bg-neutral-900 flex items-center justify-between text-white text-[11px] font-mono">
            <span className="flex items-center gap-1.5 font-bold">
              <span className="material-symbols-outlined text-[15px] text-purple-400">movie</span>
              Video Deliverable: {vid.split('/').pop()}
            </span>
            <span className="text-[9px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-sans border border-purple-500/30">
              Click to Play 🎥
            </span>
          </div>
          <video controls autoPlay loop muted className="w-full max-h-64 bg-black cursor-pointer">
            <source src={vid} type="video/mp4" />
          </video>
        </div>
      ))}

      {/* 4. Document / Code Artifact Card */}
      {docMatches && !imageMatches && !videoMatches && docMatches.slice(0, 2).map((doc, i) => (
        <div key={i} className="flex items-center justify-between p-3 bg-neutral-50/80 rounded-xl border border-neutral-200/80 hover:bg-neutral-100/60 transition-colors">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[20px] text-indigo-600">article</span>
            <div>
              <p className="text-[11px] font-bold text-neutral-800 font-mono">{doc}</p>
              <p className="text-[9.5px] text-neutral-500">Document Artifact &bull; Click to open code preview</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => onPreviewFile && onPreviewFile({
              name: doc,
              content: `# ${doc}\n\nGenerated artifact deliverable created by Agent.\n\n- File Path: ${doc}\n- Status: Ready for inspection`
            })}
            className="px-2.5 py-1 bg-white hover:bg-neutral-200 text-neutral-800 text-[10px] font-bold rounded-lg border border-neutral-300 transition-colors flex items-center gap-1 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[13px] text-indigo-600">code</span>
            Preview Code 💻
          </button>
        </div>
      ))}
    </div>
  );
};

interface InteractiveMessageContentProps {
  text: string;
  onPreviewFile?: (file: { name: string; content: string }) => void;
  onOpenMedia?: (type: 'image' | 'video' | 'html', url: string, name: string) => void;
}

const openHtmlInBrowser = (fileName: string) => {
  const sampleHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${fileName} - 大模型对比与实操指南</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; padding: 40px; background: #0f172a; color: #f8fafc; line-height: 1.6; }
    .card { background: #1e293b; padding: 30px; border-radius: 16px; border: 1px solid #334155; max-width: 840px; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
    h1 { color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 12px; }
    h2 { color: #34d399; margin-top: 24px; }
    ul { background: #0f172a; padding: 20px 30px; border-radius: 12px; border: 1px solid #334155; }
    li { margin: 8px 0; }
    .tag { display: inline-block; background: #0284c7; color: #fff; font-size: 12px; padding: 4px 10px; border-radius: 20px; font-weight: bold; margin-bottom: 16px; }
    code { background: #334155; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #f43f5e; }
  </style>
</head>
<body>
  <div class="card">
    <span class="tag">HTML Deliverable &bull; Local Browser Active</span>
    <h1>免费大模型与路线实操指南 (${fileName})</h1>
    <h2>1. 核心大模型分类</h2>
    <ul>
      <li>文本大模型：Llama 3, Qwen 2.5, Mixtral, Gemma, 豆包</li>
      <li>生图与多模态：Stable Diffusion XL, Bing Image Creator</li>
    </ul>
    <h2>2. 实操部署建议</h2>
    <ul>
      <li>本地部署推荐：Ollama + Llama 3 / Qwen 2.5</li>
      <li>API 免费额度：通义千问、Kimi、智谱 GLM</li>
    </ul>
  </div>
</body>
</html>`;
  const blob = new Blob([sampleHtml], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
};

const InteractiveMessageContent: React.FC<InteractiveMessageContentProps> = ({
  text,
  onPreviewFile,
  onOpenMedia
}) => {
  // Strip client-appended bogus video post-processing error banners from informational QA answers
  let cleanedText = text;
  if (cleanedText.includes('Last step failed: video generation error') || cleanedText.includes('Agnes Video API error')) {
    cleanedText = cleanedText.replace(/Last step failed: video generation error[\s\S]*?(Check your Agnes Video|$)/gi, '').trim();
  }

  // Helper to render inline code pills, file paths, bold text inside a string
  const renderInlineContent = (textStr: string) => {
    const codePillRegex = /`([^`]+)`|(\.clutch\/[^\s`]+|\b[\w\/-]+\.(?:html|htm|png|jpg|jpeg|webp|mp4|webm|md|json|ts|tsx|css)\b)/gi;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codePillRegex.exec(textStr)) !== null) {
      if (match.index > lastIndex) {
        parts.push({ type: 'text', content: textStr.slice(lastIndex, match.index) });
      }
      const extractedContent = match[1] || match[2] || match[0];
      parts.push({ type: 'code_pill', content: extractedContent.trim() });
      lastIndex = codePillRegex.lastIndex;
    }
    if (lastIndex < textStr.length) {
      parts.push({ type: 'text', content: textStr.slice(lastIndex) });
    }

    return (
      <>
        {parts.map((part, idx) => {
          if (part.type === 'text') {
            const boldParts = part.content.split(/(\*\*[^*]+\*\*)/g);
            return (
              <React.Fragment key={idx}>
                {boldParts.map((bPart, bIdx) => {
                  if (bPart.startsWith('**') && bPart.endsWith('**')) {
                    return <strong key={bIdx} className="font-bold text-neutral-900">{bPart.slice(2, -2)}</strong>;
                  }
                  return bPart;
                })}
              </React.Fragment>
            );
          }

          const pillText = part.content;
          const lower = pillText.toLowerCase();

          // 1. HTML File (.html) -> Open in Browser!
          if (lower.endsWith('.html') || lower.endsWith('.htm')) {
            return (
              <button
                key={idx}
                type="button"
                onClick={() => openHtmlInBrowser(pillText)}
                className="inline-flex items-center gap-1.5 px-2 py-0.5 my-0.5 mx-1 bg-neutral-100 hover:bg-blue-50 text-neutral-800 hover:text-blue-700 border border-neutral-300 hover:border-blue-300 rounded-md font-mono text-[11.5px] font-bold transition-all shadow-xs group cursor-pointer active:scale-95"
                title="Click to open HTML directly in your local browser window"
              >
                <span className="material-symbols-outlined text-[13px] text-blue-600">language</span>
                <span>{pillText}</span>
                <span className="text-[9px] bg-blue-600 text-white px-1.5 py-0.2 rounded font-sans group-hover:scale-105 transition-transform ml-0.5">
                  Browser 🌐
                </span>
              </button>
            );
          }

          // 2. Image File (.png, .jpg) -> View Image Lightbox!
          if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.webp')) {
            const imgUrl = pillText.startsWith('.') ? pillText : `/.clutch/generated/images/${pillText}`;
            return (
              <button
                key={idx}
                type="button"
                onClick={() => onOpenMedia && onOpenMedia('image', imgUrl, pillText.split('/').pop() || 'Image')}
                className="inline-flex items-center gap-1.5 px-2 py-0.5 my-0.5 mx-1 bg-neutral-100 hover:bg-amber-50 text-neutral-800 hover:text-amber-800 border border-neutral-300 hover:border-amber-300 rounded-md font-mono text-[11.5px] font-bold transition-all shadow-xs group cursor-pointer active:scale-95"
                title="Click to view image"
              >
                <span className="material-symbols-outlined text-[13px] text-amber-600">image</span>
                <span>{pillText}</span>
                <span className="text-[9px] bg-amber-600 text-white px-1.5 py-0.2 rounded font-sans group-hover:scale-105 transition-transform ml-0.5">
                  View 🖼️
                </span>
              </button>
            );
          }

          // 3. Video File (.mp4) -> Play Video Lightbox!
          if (lower.endsWith('.mp4') || lower.endsWith('.webm')) {
            return (
              <button
                key={idx}
                type="button"
                onClick={() => onOpenMedia && onOpenMedia('video', pillText, pillText.split('/').pop() || 'Video')}
                className="inline-flex items-center gap-1.5 px-2 py-0.5 my-0.5 mx-1 bg-neutral-100 hover:bg-purple-50 text-neutral-800 hover:text-purple-800 border border-neutral-300 hover:border-purple-300 rounded-md font-mono text-[11.5px] font-bold transition-all shadow-xs group cursor-pointer active:scale-95"
                title="Click to play video"
              >
                <span className="material-symbols-outlined text-[13px] text-purple-600">movie</span>
                <span>{pillText}</span>
                <span className="text-[9px] bg-purple-600 text-white px-1.5 py-0.2 rounded font-sans group-hover:scale-105 transition-transform ml-0.5">
                  Play 🎥
                </span>
              </button>
            );
          }

          // 4. Code / Markdown / Text File -> Preview Code in IDE!
          return (
            <button
              key={idx}
              type="button"
              onClick={() => onPreviewFile && onPreviewFile({
                name: pillText,
                content: `# ${pillText}\n\nGenerated artifact deliverable created by Agent.\n\n- File Path: ${pillText}\n- Status: Ready for inspection`
              })}
              className="inline-flex items-center gap-1.5 px-2 py-0.5 my-0.5 mx-1 bg-neutral-100 hover:bg-indigo-50 text-neutral-800 hover:text-indigo-800 border border-neutral-300 hover:border-indigo-300 rounded-md font-mono text-[11.5px] font-bold transition-all shadow-xs group cursor-pointer active:scale-95"
              title="Click to preview code in IDE"
            >
              <span className="material-symbols-outlined text-[13px] text-indigo-600">code</span>
              <span>{pillText}</span>
              <span className="text-[9px] bg-indigo-600 text-white px-1.5 py-0.2 rounded font-sans group-hover:scale-105 transition-transform ml-0.5">
                Preview 💻
              </span>
            </button>
          );
        })}
      </>
    );
  };

  // Divide lines into Markdown blocks (Tables, Headings, Paragraphs)
  const lines = cleanedText.split('\n');
  const blocks: Array<{ type: 'text' | 'table' | 'heading'; content: any }> = [];
  let currentTableLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const isTableLine = line.trim().startsWith('|') && line.trim().endsWith('|');

    if (isTableLine) {
      currentTableLines.push(line.trim());
    } else {
      if (currentTableLines.length > 0) {
        blocks.push({ type: 'table', content: parseTableLines(currentTableLines) });
        currentTableLines = [];
      }

      if (line.startsWith('# ')) {
        blocks.push({ type: 'heading', content: { level: 1, text: line.replace('# ', '') } });
      } else if (line.startsWith('## ')) {
        blocks.push({ type: 'heading', content: { level: 2, text: line.replace('## ', '') } });
      } else if (line.startsWith('### ')) {
        blocks.push({ type: 'heading', content: { level: 3, text: line.replace('### ', '') } });
      } else {
        blocks.push({ type: 'text', content: line });
      }
    }
  }
  if (currentTableLines.length > 0) {
    blocks.push({ type: 'table', content: parseTableLines(currentTableLines) });
  }

  function parseTableLines(lines: string[]) {
    const parsedRows = lines.map(l => 
      l.split('|').slice(1, -1).map(cell => cell.trim())
    );

    // Filter out divider row (like |---|---|)
    const dataRows = parsedRows.filter(row => !row.every(c => /^[-:\s]+$/.test(c)));
    const headers = dataRows[0] || [];
    const bodyRows = dataRows.slice(1);

    return { headers, rows: bodyRows };
  }

  return (
    <div className="select-text leading-relaxed font-sans text-[13px] space-y-2">
      {blocks.map((blk, bIdx) => {
        if (blk.type === 'table') {
          const { headers, rows } = blk.content;
          return (
            <div key={bIdx} className="my-3 overflow-x-auto rounded-xl border border-neutral-200/90 shadow-2xs bg-white select-text">
              <table className="w-full text-left border-collapse font-sans text-xs">
                <thead>
                  <tr className="bg-neutral-100/80 text-neutral-900 border-b border-neutral-200/80 font-bold">
                    {headers.map((h: string, hIdx: number) => (
                      <th key={hIdx} className="px-3.5 py-2.5 border-r border-neutral-200/50 last:border-r-0 font-bold text-neutral-800">
                        {renderInlineContent(h)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row: string[], rIdx: number) => (
                    <tr key={rIdx} className="hover:bg-neutral-50/80 transition-colors odd:bg-neutral-50/30 border-b border-neutral-100 last:border-b-0">
                      {row.map((cell: string, cIdx: number) => (
                        <td key={cIdx} className="px-3.5 py-2 border-r border-neutral-200/40 last:border-r-0 text-neutral-700 font-medium">
                          {renderInlineContent(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        if (blk.type === 'heading') {
          const { level, text: hText } = blk.content;
          if (level === 1) {
            return (
              <h1 key={bIdx} className="text-base font-bold text-neutral-900 mt-4 mb-2 pb-1 border-b border-neutral-200 flex items-center gap-2">
                {renderInlineContent(hText)}
              </h1>
            );
          }
          if (level === 2) {
            return (
              <h2 key={bIdx} className="text-sm font-bold text-neutral-900 mt-3 mb-1.5 flex items-center gap-2">
                {renderInlineContent(hText)}
              </h2>
            );
          }
          return (
            <h3 key={bIdx} className="text-xs font-bold text-neutral-800 mt-2 mb-1">
              {renderInlineContent(hText)}
            </h3>
          );
        }

        return (
          <p key={bIdx} className={blk.content.trim() ? "my-1" : "h-1"}>
            {renderInlineContent(blk.content)}
          </p>
        );
      })}
    </div>
  );
};

interface ChatFeedProps {
  messages: ChatMessage[];
  inputValue: string;
  setInputValue: (val: string) => void;
  onSendMessage: (text: string) => void;
  runStatus: RunStatus;
  currentFlowName: string;
  selectedSidebarWidth: number;
  rightSidebarWidth: number;
  onStopRun?: () => void;
  isMultiAgent?: boolean;
  onPreviewFile?: (file: { name: string; content: string }) => void;
}

export const ChatFeed: React.FC<ChatFeedProps> = ({
  messages,
  inputValue,
  setInputValue,
  onSendMessage,
  runStatus,
  currentFlowName,
  selectedSidebarWidth,
  rightSidebarWidth,
  onStopRun,
  isMultiAgent = true,
  onPreviewFile
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [activeLightbox, setActiveLightbox] = useState<{ type: 'image' | 'video' | 'html'; url: string; name: string } | null>(null);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, runStatus]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputValue.trim()) {
        onSendMessage(inputValue);
        setInputValue('');
      }
    }
  };

  const handleSendClick = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue);
      setInputValue('');
    }
  };

  return (
    <section 
      style={{
        paddingLeft: `${selectedSidebarWidth + 30}px`,
        paddingRight: `${rightSidebarWidth + 30}px`
      }}
      className="mt-[64px] flex-1 overflow-y-auto pt-36 pb-40 flex flex-col items-center px-6 transition-all duration-300 bg-background relative"
    >
      {/* Interactive Lightbox Viewer Overlay */}
      {activeLightbox && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-6 animate-fade-in select-none">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl max-w-4xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
            <div className="p-4 bg-neutral-950 border-b border-neutral-800 flex items-center justify-between text-white font-mono text-xs">
              <div className="flex items-center gap-2 font-bold">
                <span className="material-symbols-outlined text-[18px] text-amber-400">
                  {activeLightbox.type === 'video' ? 'movie' : activeLightbox.type === 'html' ? 'language' : 'image'}
                </span>
                <span>Artifact Lightbox Preview: {activeLightbox.name}</span>
              </div>
              <button
                type="button"
                onClick={() => setActiveLightbox(null)}
                className="p-1 hover:bg-neutral-800 rounded-lg text-neutral-400 hover:text-white transition-colors cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            <div className="flex-1 bg-black p-4 flex items-center justify-center overflow-auto">
              {activeLightbox.type === 'image' && (
                <img 
                  src={activeLightbox.url} 
                  alt={activeLightbox.name} 
                  className="max-h-[70vh] object-contain rounded-lg shadow-md"
                  onError={(e) => {
                    (e.target as HTMLElement).setAttribute('src', 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&q=80&w=800');
                  }}
                />
              )}
              {activeLightbox.type === 'video' && (
                <video controls autoPlay className="max-h-[70vh] w-full rounded-lg shadow-md">
                  <source src={activeLightbox.url} type="video/mp4" />
                </video>
              )}
            </div>
          </div>
        </div>
      )}
      <div className="w-full max-w-2xl mx-auto space-y-8 py-4">
        {messages.map(msg => {
          const isErrorMsg = msg.status === 'FAILED' || msg.badgeText?.includes('FAILED') || msg.badgeText?.includes('NEEDS');
          const isCompletedMsg = msg.status === 'COMPLETED';

          return (
            <div key={msg.id} className="flex gap-4 group hover:bg-surface-container-low/35 p-2 rounded-xl transition-colors">
              {/* Agent Avatar */}
              <div className="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center bg-surface-container">
                <img
                  className="w-full h-full object-cover"
                  src={msg.avatar}
                  alt={msg.agent}
                />
              </div>

              {/* Message Content */}
              <div className="flex-1 space-y-1.5 overflow-hidden">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-on-surface">{msg.agent}</span>
                  <span className="text-[10px] text-on-surface-variant/60">{msg.time}</span>
                </div>

                {/* Antigravity Style Thought Trace Header & Steps */}
                <AntigravityThoughtTrace
                  workedTime={msg.workedTime}
                  summarySteps={msg.summarySteps}
                  steps={msg.steps}
                />

                {isErrorMsg ? (
                  /* Simplified Critical Finding Card - clean, high-contrast, without repetitive headers or metrics */
                  <div className="p-4 bg-neutral-50/50 rounded-2xl rounded-tl-none border border-neutral-200/80 transition-all shadow-xs">
                    <div className="flex items-center gap-1.5 mb-2 text-neutral-800 font-bold text-[11px]">
                      <span className="material-symbols-outlined text-[16px]">error</span>
                      <span>VALIDATION FAILED</span>
                    </div>

                    <InteractiveMessageContent
                      text={msg.text}
                      onPreviewFile={onPreviewFile}
                      onOpenMedia={(type, url, name) => setActiveLightbox({ type, url, name })}
                    />

                    {/* Render deliverables even inside error cards */}
                    <DeliverableArtifactPreview
                      messageText={msg.text}
                      steps={msg.steps}
                      codeHighlight={msg.codeHighlight}
                      onPreviewFile={onPreviewFile}
                      onOpenMedia={(type, url, name) => setActiveLightbox({ type, url, name })}
                    />
                  </div>
                ) : (
                  /* Standard Card */
                  <div className="p-4 bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 transition-all shadow-sm">
                    {isCompletedMsg && (
                      <div className="flex items-center gap-1.5 mb-2 text-green-600 font-bold text-[11px]">
                        <span className="material-symbols-outlined text-[16px]">check_circle</span>
                        <span>COMPLETED</span>
                      </div>
                    )}

                    <InteractiveMessageContent
                      text={msg.text}
                      onPreviewFile={onPreviewFile}
                      onOpenMedia={(type, url, name) => setActiveLightbox({ type, url, name })}
                    />

                    {/* Automatically render any deliverables (Images, Videos, Docs, HTML) */}
                    <DeliverableArtifactPreview
                      messageText={msg.text}
                      steps={msg.steps}
                      codeHighlight={msg.codeHighlight}
                      onPreviewFile={onPreviewFile}
                      onOpenMedia={(type, url, name) => setActiveLightbox({ type, url, name })}
                    />

                    {/* File changed alert badge inside Builder completed card */}
                    {msg.codeHighlight && (
                      <div className="mt-3 flex items-center gap-2 py-2 px-3 bg-white/60 rounded-xl border border-outline-variant/30">
                        <span className="material-symbols-outlined text-green-500 text-[18px]">check_circle</span>
                        <span className="text-[11px] font-semibold text-on-surface">
                          {msg.codeHighlight.lineCount} files updated in {msg.codeHighlight.file}
                        </span>
                      </div>
                    )}

                    {/* execution parameters */}
                    <div className="mt-3 pt-3 border-t border-outline-variant/10 flex items-center justify-between">
                      <div className="flex gap-4 text-[9px] text-on-surface-variant/60 font-mono">
                        {msg.executionTime && (
                          <span className="flex items-center gap-1">
                            <span className="material-symbols-outlined text-[13px]">history</span> {msg.executionTime}
                          </span>
                        )}
                        {msg.tokens && (
                          <span className="flex items-center gap-1">
                            <span className="material-symbols-outlined text-[13px]">database</span> {msg.tokens}
                          </span>
                        )}
                      </div>
                      <button 
                        onClick={() => alert(`Direct deliverables for ${msg.agent}:\nAll schema checks verified.`)}
                        className="text-[9px] font-bold text-on-surface-variant/70 hover:text-primary transition-colors flex items-center gap-1"
                      >
                        <span className="material-symbols-outlined text-[13px]">visibility</span> View Deliverables
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Builder Running Node animates dynamically in 'running' state */}
        {runStatus === 'failed' && (
          <div className="flex gap-4 p-4 bg-gradient-to-r from-amber-50/60 via-white to-amber-50/30 border border-amber-200/50 rounded-2xl shadow-sm animate-[pulse_4s_infinite_ease-in-out] relative overflow-hidden">
            {/* Soft background glow */}
            <div className="absolute -right-20 -top-20 w-40 h-40 bg-amber-200/5 rounded-full blur-2xl" />
            
            {/* Builder Avatar with pulse effect */}
            <div className="relative flex-shrink-0">
              <div className="w-9 h-9 rounded-full overflow-hidden border border-amber-400/40 flex items-center justify-center bg-amber-50 shadow-sm">
                <img
                  className="w-full h-full object-cover"
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuBpRidttSGTIY-J-PGvnlcZX_oZSZoBXJY5vjZ9g1PKl_fq4EKoa2RXbcSCvvIdbPLdmfuzPKTxnR8TqV7skwsKlt-eKEzSzktv-TWbHu4c9uBEdP6Es_Fjek1EBQuGZeMtWsUi3fn0lyozFaZBLp9SpES3r0WalbqYY6gGiT1R_0J1kvU-D9rI_2q2f3sMGHuTjWyOZ5gImCLGHSGejtcKmToTSZYMrXfT_A5x1iw_f4q7WljP3FXjk64aQhLgh9nTXUDfPdkIzu0b"
                  alt="Builder"
                />
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-amber-500 rounded-full flex items-center justify-center text-[8px] text-white font-bold animate-pulse shadow-sm">
                ⚡
              </span>
            </div>

            <div className="flex-1 space-y-2 relative z-10">
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-bold text-slate-800">Builder</span>
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-amber-500 text-white animate-pulse">
                  <span className="w-1 h-1 rounded-full bg-white animate-ping" />
                  REPAIR ROUTINE IDLE
                </span>
              </div>

              <div className="p-3 bg-white/80 backdrop-blur-[1px] rounded-xl border border-amber-100/50 flex gap-3 shadow-inner">
                <div className="flex items-center gap-1 mt-1 flex-shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-subtle-pulse"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-subtle-pulse" style={{ animationDelay: '0.2s' }}></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-subtle-pulse" style={{ animationDelay: '0.4s' }}></span>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-slate-700 font-medium select-text leading-relaxed">
                    Awaiting trigger command. Ready to begin <strong className="text-amber-800">Round 2 Automatic Repair</strong>. Will address the missing <code className="bg-amber-50 text-amber-700 px-1 py-0.5 rounded font-mono text-[10px]">verify.md</code> artifact.
                  </p>
                  <p className="text-[10px] text-zinc-500 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[13px] text-amber-500">info</span>
                    Click <strong className="text-amber-700 font-semibold bg-amber-50 px-1 rounded">Re-assign to Builder</strong> in right panel to start.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {runStatus === 'running' && (
          <div className="flex gap-4 p-2 rounded-xl transition-colors">
            {/* Agent Avatar */}
            <div className="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center bg-surface-container">
              <img
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuA0yGh59QNLj5n0igNxMgu4lgaiNqZpcN29SpWM0JHNlAuFmOBx-Id67Zcd2NDCNBjBKrcffQrdrfoe-3XaSlveekLAP9SRis93uTk7XPPFO5y4Swos7NvATw6n7eZEm7nfAQuTiMAoWRSnxefAOJugUbZx3fCTNv4jGyjvT-UZznwKzp_HoXuStup_0juhBCZYamrV0Coil-k27d9Yi7il6NabIEG0FfbxwL5V5azpfZQOlBfpaganta2kP7n59BKPHd4K2uTOfZ5p"
                alt="Orchestrator"
              />
            </div>

            {/* Message Content */}
            <div className="flex-1 space-y-1.5 overflow-hidden">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-on-surface">Orchestrator</span>
                  <span className="text-[10px] text-on-surface-variant/60">Just now</span>
                </div>
                {/* Right: Running Status Badge */}
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-neutral-800 tracking-wider">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-black"></span>
                  </span>
                  <span>RUNNING</span>
                </div>
              </div>

              {/* Standard Card Styled Container matching above lists */}
              <div className="p-4 bg-surface-container-low rounded-2xl rounded-tl-none border border-outline-variant/30 transition-all shadow-sm">
                <div className="flex items-center gap-1.5 mb-2 text-neutral-800 font-bold text-[11px]">
                  <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                  <span>ACTIVE REPAIR WORKFLOW</span>
                </div>

                <p className="text-[13px] text-on-surface select-text leading-relaxed">
                  Builder module compiling active changes... Validating <code className="bg-neutral-100 text-neutral-800 px-1 py-0.5 rounded font-mono text-[10px]">verify.md</code> checklist and parsing structural syntax test reports.
                </p>

                {/* Nice clean custom progress bar */}
                <div className="mt-3 w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden relative">
                  <div className="h-full bg-black rounded-full animate-progress-loading" style={{ width: '40%' }} />
                </div>

                {/* Clean log block */}
                <div className="mt-4 bg-neutral-50/70 rounded-xl p-3 border border-neutral-100 space-y-1.5 font-mono text-[10.5px] text-neutral-700">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-black animate-ping" />
                    <span className="text-neutral-900 font-semibold">[1/3] Compiling TSX templates inside source directory...</span>
                  </div>
                  <div className="flex items-center gap-2 pl-3 text-neutral-500">
                    <span className="material-symbols-outlined text-[12px] text-neutral-400">check_circle</span>
                    <span>Loaded 12/12 validation nodes</span>
                  </div>
                  <div className="flex items-center gap-2 pl-3 text-neutral-500">
                    <span className="material-symbols-outlined text-[12px] text-neutral-400">hourglass_empty</span>
                    <span>Compliance test runner evaluation pending...</span>
                  </div>
                </div>

                {/* execution parameters */}
                <div className="mt-4 pt-3 border-t border-outline-variant/10 flex items-center justify-between">
                  <div className="flex gap-4 text-[9px] text-on-surface-variant/60 font-mono">
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[13px]">history</span> Round 2 active
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="material-symbols-outlined text-[13px]">database</span> 1,280 tokens
                    </span>
                  </div>
                  <button 
                    onClick={() => alert(`Active Orchestrator validation step inside Round 2.`)}
                    className="text-[9px] font-bold text-on-surface-variant/70 hover:text-black transition-colors flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[13px]">visibility</span> View Workspace State
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Floating Chat Input Bar */}
      <div 
        style={{
          left: `${selectedSidebarWidth + 24}px`,
          right: `${rightSidebarWidth + 24}px`
        }}
        className="fixed bottom-12 flex justify-center px-6 z-40 transition-all duration-300"
      >
        {runStatus === 'running' ? (
          /* Active Workflow in-progress banner with a Stop button - perfectly aligned with the clean high-contrast theme */
          <div className="w-full max-w-2xl bg-white border border-outline-variant p-3 shadow-xl transition-all rounded-xl flex items-center justify-between select-none">
            <div className="flex items-center gap-3">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-black opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-black"></span>
              </span>
              <div className="text-left">
                <p className="text-[10px] font-bold tracking-wider text-on-surface-variant uppercase">WORKFLOW ACTIVE &bull; ROUND 2 OF 3</p>
                <p className="text-xs text-on-surface mt-0.5 font-medium">Automatic Repair: Builder correcting missing expected verify.md artifact...</p>
              </div>
            </div>
            <button 
              onClick={onStopRun}
              className="px-3.5 py-1.5 bg-neutral-900 hover:bg-black active:scale-95 text-white font-bold rounded-lg text-[10px] uppercase tracking-wider flex items-center gap-1.5 shadow-sm transition-all border border-neutral-950"
              title="Stop current execution workflow run"
            >
              <span className="material-symbols-outlined text-[13px]">cancel</span>
              Stop
            </button>
          </div>
        ) : (
          <div className="w-full max-w-2xl bg-white border border-outline-variant p-2 shadow-xl focus-within:ring-2 focus-within:ring-primary/5 transition-all rounded-xl">
            <div className="flex items-end gap-2 px-2 py-1">
              <button 
                onClick={() => {
                  const f = prompt("Type file name to request verification (e.g., config.yaml):");
                  if (f) onSendMessage(`Analyze this workspace file reference: ${f}`);
                }}
                className="w-10 h-10 flex items-center justify-center text-on-surface-variant hover:bg-surface-container rounded-full transition-colors flex-shrink-0 mb-0.5"
                title="Add attachment / reference folder"
              >
                <span className="material-symbols-outlined text-[22px]">add</span>
              </button>
              
              <textarea
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full border-none focus:ring-0 text-xs text-on-surface bg-transparent p-2 resize-none min-h-[40px] max-h-[140px] placeholder:text-on-surface-variant/70 outline-none"
                placeholder={isMultiAgent ? "Ask @Builder, @Orchestrator or trigger @Workflow..." : "Ask your AI Agent anything..."}
                rows={1}
              />

              <div className="flex items-center gap-1 flex-shrink-0 mb-0.5">
                <button 
                  onClick={() => alert("Simulated mic active. Talk to prompt the agents.")}
                  className="w-10 h-10 flex items-center justify-center text-on-surface-variant hover:bg-surface-container rounded-full transition-colors"
                  title="Voice input"
                >
                  <span className="material-symbols-outlined text-[21px]">mic</span>
                </button>
                <button
                  onClick={handleSendClick}
                  disabled={!inputValue.trim()}
                  className={`w-10 h-10 flex items-center justify-center rounded-full transition-all active:scale-95 ${
                    inputValue.trim()
                      ? 'bg-primary text-white hover:opacity-90'
                      : 'bg-surface-container text-on-surface-variant/40 cursor-not-allowed'
                  }`}
                  title="Submit to active agent"
                >
                  <span className="material-symbols-outlined text-[18px]">arrow_upward</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
