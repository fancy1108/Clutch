import React, { useEffect, useRef } from 'react';
import type { DispatchLogEntry } from '../../types';
import { isHandoffDispatchEntry } from '../../services/terminalOrchestraUtils';
import { USER_CHAT_AVATAR } from '../../services/clutchState';
import { resolveBrandLogoSrc } from '../../services/brandLogos';
import { useLanguage } from '../LanguageContext';
import { AgentChatAvatar } from '../AgentChatAvatar';
import { LegacyIcon } from '../ui/LegacyIcon';
import { HandoffPreviewModal } from './HandoffPreviewModal';
import { TerminalSessionCommandCard } from './TerminalSessionCommandCard';

interface MentionableAgent {
  id: string;
  name: string;
  logo?: string;
  dispatchTarget: string;
  agentType?: string;
}

interface TerminalDispatchHistoryFeedProps {
  entries: DispatchLogEntry[];
  highlightedEntryId?: string | null;
  userAvatar?: string;
  userName?: string;
  mentionableAgents?: MentionableAgent[];
  workspacePath?: string;
}

function formatDispatchTime(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return iso;
  return new Date(parsed).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function resolveAgentForTarget(
  target: string,
  agents: MentionableAgent[],
): MentionableAgent | undefined {
  const needle = target.trim().toLowerCase();
  return agents.find(
    (agent) =>
      agent.dispatchTarget.trim().toLowerCase() === needle
      || agent.name.trim().toLowerCase() === needle,
  );
}

function resolveAgentLogo(target: string, agents: MentionableAgent[]): string | undefined {
  const match = resolveAgentForTarget(target, agents);
  if (match?.logo) return match.logo;
  if (match?.agentType) {
    return resolveBrandLogoSrc({ toolId: match.agentType, runtimeEngine: match.dispatchTarget });
  }
  return resolveBrandLogoSrc({ runtimeEngine: target });
}

export const TerminalDispatchHistoryFeed: React.FC<TerminalDispatchHistoryFeedProps> = ({
  entries,
  highlightedEntryId = null,
  userAvatar,
  userName = 'User',
  mentionableAgents = [],
  workspacePath,
}) => {
  const { t } = useLanguage();
  const [previewPath, setPreviewPath] = React.useState<string | null>(null);
  const highlightedRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!highlightedEntryId || !highlightedRef.current) return;
    highlightedRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [highlightedEntryId, entries]);

  if (entries.length === 0) {
    return (
      <p className="text-sm text-on-surface-variant text-center py-12">
        {t('No dispatch records yet')}
      </p>
    );
  }

  const avatarUrl = userAvatar || USER_CHAT_AVATAR;

  return (
    <>
      <div data-testid="terminal-dispatch-history-feed" className="space-y-8 py-2">
        {entries.map((entry) => {
          const isHandoff = isHandoffDispatchEntry(entry);
          const isHighlighted = highlightedEntryId === entry.id;
          const agentName = entry.target;
          const agentLogo = resolveAgentLogo(entry.target, mentionableAgents);
          const timeLabel = formatDispatchTime(entry.time);

          return (
            <div
              key={entry.id}
              id={`dispatch-history-${entry.id}`}
              ref={isHighlighted ? highlightedRef : undefined}
              className={`space-y-8 rounded-2xl transition-colors ${
                isHighlighted ? 'ring-2 ring-primary/20 bg-primary/5 p-3 -mx-3' : ''
              }`}
            >
              {/* User prompt */}
              <div className="w-full flex justify-end">
                <div className="flex gap-4 max-w-[85%] flex-row-reverse group p-2 rounded-xl">
                  <div className="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center bg-surface-container">
                    <img
                      className="w-full h-full object-contain p-1"
                      src={avatarUrl}
                      alt={userName}
                    />
                  </div>
                  <div className="flex-1 space-y-1.5 overflow-hidden">
                    <div className="flex items-center gap-2 justify-end">
                      <span className="text-[10px] text-on-surface-variant/60">{timeLabel}</span>
                      <span className="text-xs font-bold text-on-surface">{userName}</span>
                    </div>
                    <div className="p-4 rounded-2xl border border-outline-variant/30 shadow-sm bg-primary/10 text-on-surface rounded-tr-none text-left">
                      <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                        {entry.prompt}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Agent handoff / dispatch response */}
              <div className="w-full flex justify-start">
                <div className="flex gap-4 max-w-[85%] group p-2 rounded-xl">
                  <AgentChatAvatar src={agentLogo} alt={agentName} />
                  <div className="flex-1 space-y-1.5 overflow-hidden">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-on-surface">{agentName}</span>
                      <span className="text-[10px] text-on-surface-variant/60">{timeLabel}</span>
                    </div>
                    {isHandoff ? (
                      <button
                        type="button"
                        onClick={() => setPreviewPath(entry.handoff_path)}
                        className="w-full text-left p-4 rounded-2xl border border-outline-variant/30 shadow-sm bg-surface-container-low rounded-tl-none hover:bg-surface-container-high hover:border-primary/30 transition-colors group/handoff"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <LegacyIcon
                            name="description"
                            className="text-[16px] text-primary group-hover/handoff:text-primary"
                          />
                          <span className="text-[11px] font-bold text-on-surface">
                            {entry.sources_label} → {entry.target}
                          </span>
                        </div>
                        <p className="text-[10px] font-mono text-on-surface-variant truncate mb-2">
                          {entry.handoff_file || entry.handoff_path}
                        </p>
                        <span className="text-[11px] font-semibold text-primary">
                          {t('Preview handoff')} →
                        </span>
                      </button>
                    ) : (
                      <div className="p-4 rounded-2xl border border-outline-variant/30 shadow-sm bg-surface-container-low rounded-tl-none">
                        <p className="text-sm text-on-surface-variant leading-relaxed">
                          {t('Terminal dispatch executed')}
                        </p>
                      </div>
                    )}
                    {(entry.lane_sessions?.length ?? 0) > 0 ? (
                      <div className="mt-3 space-y-2">
                        <p className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/80">
                          {t('Terminal session IDs')}
                        </p>
                        {entry.lane_sessions!.map((laneSession) => (
                          <TerminalSessionCommandCard
                            key={`${entry.id}-${laneSession.lane_id}`}
                            session={laneSession}
                            workspacePath={workspacePath}
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {previewPath ? (
        <HandoffPreviewModal path={previewPath} onClose={() => setPreviewPath(null)} />
      ) : null}
    </>
  );
};
