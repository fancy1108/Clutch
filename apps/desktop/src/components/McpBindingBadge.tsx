/**
 * D40 — Chat chrome: bound MCP count / unbound CTA (composer + menu row).
 */
import React, { useEffect, useState } from 'react';
import { fetchMcpStatus } from '../services/mcpApi';
import { buildMcpBindingSummary } from '../services/agentMcpSummary';
import { useLanguage } from './LanguageContext';
import { LegacyIcon } from './ui/LegacyIcon';

type McpBindingBadgeProps = {
  mcpServerIds?: string[];
  /** Only show for Clutch Agent sessions. */
  visible?: boolean;
  onOpenBind?: () => void;
  /** Full-width row inside the + menu. */
  variant?: 'inline' | 'menu';
};

const menuRowClass =
  'w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left';

export const McpBindingBadge: React.FC<McpBindingBadgeProps> = ({
  mcpServerIds,
  visible = true,
  onOpenBind,
  variant = 'inline',
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
        title={t('Bind MCP')}
        aria-label={t('Bind MCP')}
        className={
          variant === 'menu'
            ? menuRowClass
            : 'inline-flex h-7 items-center gap-1 rounded-lg px-1.5 text-[11px] font-semibold text-primary hover:bg-primary/10 transition-colors'
        }
      >
        {variant === 'menu' ? (
          <>
            <LegacyIcon name="hub" className="text-[17px] text-on-surface-variant" />
            {t('Bind MCP')}
          </>
        ) : (
          <span className="text-[10px]">MCP</span>
        )}
      </button>
    );
  }

  return (
    <div className={variant === 'menu' ? 'relative' : 'relative'}>
      <button
        type="button"
        data-testid="chat-mcp-badge"
        onClick={() => setOpen((value) => !value)}
        className={
          variant === 'menu'
            ? menuRowClass
            : 'inline-flex h-7 items-center rounded-lg px-1.5 text-[10px] font-mono font-semibold text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors'
        }
        title={summary.names.join(', ')}
      >
        {variant === 'menu' ? (
          <>
            <LegacyIcon name="hub" className="text-[17px] text-on-surface-variant" />
            <span>
              {summary.serverCount} MCP
              {summary.approxTools > 0 ? ` · ~${summary.approxTools}` : ''}
            </span>
          </>
        ) : (
          <>
            {summary.serverCount} MCP
            {summary.approxTools > 0 ? ` · ~${summary.approxTools}` : ''}
          </>
        )}
      </button>
      {open ? (
        <div
          data-testid="chat-mcp-badge-popover"
          className={`absolute z-50 min-w-[160px] rounded-lg border border-outline-variant/50 bg-white shadow-lg p-2 ${
            variant === 'menu' ? 'left-full top-0 ml-1' : 'bottom-full mb-1 left-0'
          }`}
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
