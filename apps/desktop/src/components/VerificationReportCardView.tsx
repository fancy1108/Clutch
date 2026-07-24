/**
 * D5 / D50 — in-chat verification report card.
 */
import React from 'react';
import { LegacyIcon } from './ui/LegacyIcon';
import type { VerificationReport as VerificationReportData } from '../types';
import {
  CHAT_AGENT_CARD,
  ChatAgentCardHeader,
  ChatAgentCardStatus,
  type ChatCardStatusTone,
} from './chatAgentCard';
import { BTN_SECONDARY_SM } from './ui/buttonStyles';

function stepIcon(status: string): string {
  if (status === 'passed') return 'check_circle';
  if (status === 'skipped') return 'check_box_outline_blank';
  return 'error';
}

function stepClass(status: string): string {
  if (status === 'passed') return 'text-green-600';
  if (status === 'skipped') return 'text-on-surface-variant/55';
  return 'text-rose-600';
}

export function VerificationReportCardView({
  report,
  t,
  onOpenChangedFile,
}: {
  report: VerificationReportData;
  t: (key: string) => string;
  onOpenChangedFile?: (path: string) => void;
}) {
  const passed = report.conclusion === 'passed';
  const tone: ChatCardStatusTone = passed ? 'success' : 'danger';
  const statusLabel = passed ? t('Verification passed') : t('Verification failed');
  const changed = report.changedFiles ?? [];

  return (
    <div
      className={CHAT_AGENT_CARD}
      data-testid="verification-report-card"
      data-conclusion={report.conclusion}
    >
      <ChatAgentCardHeader
        icon={passed ? 'check_circle' : 'error'}
        title={report.title}
        status={<ChatAgentCardStatus tone={tone}>{statusLabel}</ChatAgentCardStatus>}
      />
      {report.summary ? (
        <p className="px-3 pt-2.5 text-[12px] text-on-surface leading-relaxed">{report.summary}</p>
      ) : null}
      <ul className="px-3 py-2.5 space-y-1.5">
        {report.steps.map((step) => (
          <li key={step.id} className="flex items-start gap-2 text-[12px] leading-snug">
            <LegacyIcon
              name={stepIcon(step.status)}
              className={`text-[15px] mt-0.5 flex-shrink-0 ${stepClass(step.status)}`}
            />
            <span className="min-w-0 flex-1">
              <span className="text-on-surface font-medium">{step.name}</span>
              {step.detail ? (
                <span className="block text-[11px] text-on-surface-variant mt-0.5">
                  {step.detail}
                </span>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
      {!passed && report.nextActions && report.nextActions.length > 0 ? (
        <div className="px-3 pb-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-1">
            {t('Next actions')}
          </p>
          <ul className="space-y-1">
            {report.nextActions.map((action) => (
              <li
                key={action.slice(0, 48)}
                className="text-[12px] text-on-surface leading-snug flex gap-2"
              >
                <span className="text-on-surface-variant/70 shrink-0">•</span>
                <span className="min-w-0 flex-1">{action}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {changed.length > 0 && onOpenChangedFile ? (
        <div className="px-3 pb-3 flex flex-wrap gap-1.5">
          <button
            type="button"
            data-testid="verification-view-changes"
            className={BTN_SECONDARY_SM}
            onClick={() => onOpenChangedFile(changed[0])}
          >
            {t('View changes')}
          </button>
          {changed.slice(0, 4).map((path) => (
            <button
              key={path}
              type="button"
              className={`${BTN_SECONDARY_SM} font-mono text-[10px] max-w-[10rem] truncate`}
              title={path}
              onClick={() => onOpenChangedFile(path)}
            >
              {path.split('/').pop() || path}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
