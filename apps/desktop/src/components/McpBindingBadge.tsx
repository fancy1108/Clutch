/**
 * D40 — Chat chrome: bound MCP count / unbound CTA.
 */
import React, { useEffect, useState } from 'react';
import { fetchMcpStatus } from '../services/mcpApi';
import { buildMcpBindingSummary } from '../services/agentMcpSummary';
import { useLanguage } from './LanguageContext';

type McpBindingBadgeProps = {
  mcpServerIds?: string[];
  /** Only show for Clutch Agent sessions. */
  visible?: boolean;
  onOpenBind?: () => void;
};

export const McpBindingBadge: React.FC<McpBindingBadgeProps> = ({
  mcpServerIds,
  visible = true,
  onOpenBind,
}) => {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [summary, setSummary] = useState(() =>
    buildMcpBindingSummary(mcpServerIds, []),
  );

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    void (async () => {
      try {
        const status = await fetchMcpStatus();
        if (cancelled) return;
        setSummary(buildMcpBindingSummary(mcpServerIds, status.servers));
      } catch {
        if (!cancelled) setSummary(buildMcpBindingSummary(mcpServerIds, []));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [mcpServerIds, visible]);

  if (!visible) return null;

  if (summary.unbound) {
    return (
      <button
        type="button"
        data-testid="chat-mcp-bind-cta"
        onClick={onOpenBind}
        className="text-[10px] font-semibold text-primary hover:underline px-1.5 py-0.5 rounded-md hover:bg-primary/10"
      >
        {t('Bind MCP')}
      </button>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        data-testid="chat-mcp-badge"
        onClick={() => setOpen((value) => !value)}
        className="text-[10px] font-mono font-semibold text-on-surface-variant hover:text-on-surface px-1.5 py-0.5 rounded-md hover:bg-surface-container-high border border-outline-variant/40"
        title={summary.names.join(', ')}
      >
        {summary.serverCount} MCP
        {summary.approxTools > 0 ? ` · ~${summary.approxTools}` : ''}
      </button>
      {open ? (
        <div
          data-testid="chat-mcp-badge-popover"
          className="absolute bottom-full mb-1 left-0 z-50 min-w-[160px] rounded-lg border border-outline-variant/50 bg-white shadow-lg p-2"
        >
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wide mb-1">
            {t('Bound MCP')}
          </p>
          <ul className="space-y-0.5">
            {summary.names.map((name) => (
              <li key={name} className="text-[11px] text-on-surface truncate">
                {name}
              </li>
            ))}
          </ul>
          {onOpenBind ? (
            <button
              type="button"
              className="mt-1.5 text-[10px] font-semibold text-primary hover:underline"
              onClick={() => {
                setOpen(false);
                onOpenBind();
              }}
            >
              {t('Manage bindings')}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};
