import React, { useState } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { ChevronDown, ChevronRight, History } from 'lucide-react';
import { useLanguage } from '../../LanguageContext';
import type { DesignRound } from '../../../services/designApi';

type AgentLogData = {
  round: DesignRound | null;
  fallbackPrompt?: string;
};

export function formatDesignTokenTag(entry: {
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

export function designModelLabel(entry: { model_name?: string; model_id?: string }): string | null {
  const raw = (entry.model_name || entry.model_id || '').trim();
  if (!raw) return null;
  if (!raw.includes('-') || /\s/.test(raw)) return raw;
  return raw
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => (/^\d/.test(part) ? part : part.charAt(0).toUpperCase() + part.slice(1)))
    .join(' ');
}

export function AgentLogCardNode({ data }: NodeProps) {
  const { t } = useLanguage();
  const d = data as AgentLogData;
  const [reasoningOpen, setReasoningOpen] = useState(true);
  const round = d.round;
  const hasReasoning = Boolean(round?.reasoning_content?.trim());
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
