import { useState } from 'react';
import { Check, Copy, ExternalLink } from 'lucide-react';

import { useLanguage } from '../LanguageContext';
import { installGuideForTool, type CliInstallGuide } from '../../services/cliInstallGuides';
import type { AiToolStatus } from '../../services/toolsApi';
import { AiToolIcon } from '../AiToolIcon';

interface CliInstallGuideCardProps {
  tool: Pick<AiToolStatus, 'id' | 'name' | 'description' | 'kind'>;
  defaultExpanded?: boolean;
}

export function CliInstallGuideCard({ tool, defaultExpanded = false }: CliInstallGuideCardProps) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);
  const guide: CliInstallGuide = installGuideForTool(tool.id, tool.name);

  const copyCmd = () => {
    void navigator.clipboard.writeText(guide.cmd);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-dashed border-neutral-200 bg-neutral-50/80 p-3 text-left">
      <div className="flex items-start gap-3">
        <AiToolIcon tool={tool as AiToolStatus} dimmed />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold text-neutral-800">{tool.name}</p>
          <p className="text-[10px] text-neutral-500 mt-0.5 leading-relaxed">{tool.description}</p>
          <span className="inline-block mt-1.5 text-[9px] font-mono uppercase tracking-wide text-neutral-400 bg-white border border-neutral-200 px-1.5 py-0.5 rounded">
            {t('Not installed')}
          </span>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid={`install-guide-toggle-${tool.id}`}
          onClick={() => setExpanded((value) => !value)}
          className="text-[10px] font-semibold text-indigo-600 hover:text-indigo-800"
        >
          {expanded ? t('Hide install guide') : t('Show install guide')}
        </button>
        {guide.url ? (
          <a
            href={guide.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] font-semibold text-neutral-500 hover:text-neutral-700 inline-flex items-center gap-0.5"
          >
            {t('Visit website')}
            <ExternalLink className="h-3 w-3" />
          </a>
        ) : null}
      </div>
      {expanded ? (
        <div className="mt-2 rounded-lg border border-neutral-800 bg-neutral-900 p-3 text-left">
          <p className="text-[10px] text-neutral-400 leading-relaxed font-sans">{guide.desc}</p>
          <div className="mt-2 flex items-start justify-between gap-2 rounded border border-neutral-800 bg-neutral-950/80 p-2">
            <code className="text-[10px] font-mono text-neutral-100 break-all select-all">{guide.cmd}</code>
            <button
              type="button"
              onClick={copyCmd}
              className="shrink-0 rounded p-1 text-neutral-400 hover:bg-neutral-800 hover:text-white"
              aria-label={t('Copy command')}
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
