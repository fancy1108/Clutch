import React, { useState } from 'react';
import { Check, Copy, Terminal } from 'lucide-react';
import type { DispatchLaneSession } from '../../types';
import {
  buildTerminalHistoryCommand,
  hasTerminalHistoryCommand,
  resolveTerminalHistoryWorkspacePath,
} from '../../services/terminalSessionCommands';
import { useLanguage } from '../LanguageContext';

interface TerminalSessionCommandCardProps {
  session: DispatchLaneSession;
  compact?: boolean;
  workspacePath?: string;
}

export const TerminalSessionCommandCard: React.FC<TerminalSessionCommandCardProps> = ({
  session,
  compact = false,
  workspacePath,
}) => {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!hasTerminalHistoryCommand(session)) return null;

  const resolvedWorkspacePath = resolveTerminalHistoryWorkspacePath(session, workspacePath);
  const { cmd, descKey } = buildTerminalHistoryCommand(
    session.agent_type,
    session.cli_session_id,
    resolvedWorkspacePath,
  );
  const sessionId = session.cli_session_id.trim();

  const copyText = async (text: string) => {
    if (!text.trim()) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`rounded-xl border border-dashed border-outline-variant/40 bg-surface-container-low/60 ${
        compact ? 'p-2' : 'p-2.5'
      }`}
    >
      <div className="flex items-start gap-2 min-w-0">
        <Terminal className="w-3.5 h-3.5 shrink-0 text-on-surface-variant mt-0.5" strokeWidth={2.25} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-semibold text-on-surface">{session.label}</span>
            {sessionId ? (
              <button
                type="button"
                className="text-[9px] font-mono text-primary hover:underline truncate max-w-full"
                title={sessionId}
                onClick={() => void copyText(sessionId)}
              >
                {sessionId}
              </button>
            ) : null}
          </div>
          <button
            type="button"
            className="mt-1 text-[10px] font-semibold text-primary hover:text-primary/80"
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? t('Hide terminal command') : t('View in terminal')}
          </button>
        </div>
      </div>
      {expanded ? (
        <div className="mt-2 rounded-lg border border-neutral-800 bg-neutral-900 p-2.5 text-left">
          <p className="text-[10px] text-neutral-400 leading-relaxed font-sans">{t(descKey)}</p>
          {sessionId ? (
            <p className="mt-1.5 text-[9px] font-mono text-neutral-500 break-all">
              {t('Session ID')}: {sessionId}
            </p>
          ) : null}
          {cmd ? (
            <div className="mt-2 flex items-start justify-between gap-2 rounded border border-neutral-800 bg-neutral-950/80 p-2">
              <code className="text-[10px] font-mono text-neutral-100 break-all select-all">{cmd}</code>
              <button
                type="button"
                onClick={() => void copyText(cmd)}
                className="shrink-0 rounded p-1 text-neutral-400 hover:bg-neutral-800 hover:text-white"
                aria-label={t('Copy command')}
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};
