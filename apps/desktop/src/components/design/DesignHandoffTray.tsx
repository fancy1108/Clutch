import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ExternalLink, Loader2, X } from 'lucide-react';
import { useLanguage } from '../LanguageContext';
import { BTN_PRIMARY, BTN_SECONDARY, BTN_SUCCESS } from '../ui/buttonStyles';
import {
  approveDesignPrototype,
  approveDesignReact,
  generateDesignReact,
  sendDesignToCoding,
  startDesignPreview,
  stopDesignPreview,
  type CodingHandoff,
  type DesignSession,
} from '../../services/designApi';

type Props = {
  runId: string;
  session: DesignSession | null;
  busy: boolean;
  previewUrl: string | null;
  onClose: () => void;
  onSession: (next: DesignSession) => void;
  onPreviewUrl: (url: string | null) => void;
  onBusy: <T>(fn: () => Promise<T>) => Promise<T | undefined>;
  onSendToCoding: (handoff: CodingHandoff) => void;
};

type HandoffStep = 1 | 2 | 3 | 4;
type BusyAction = 'approve' | 'generate' | 'preview' | 'approve_react' | 'send' | null;

function stepFromSession(session: DesignSession | null): HandoffStep {
  if (!session?.prototype_approved) return 1;
  if (!session?.react_ready) return 2;
  if (!session?.react_approved) return 3;
  return 4;
}

const STEP_LABELS = [
  'Approve prototype',
  'Generate UI code',
  'Preview & approve',
  'Send to Coding',
] as const;

/** Fit a desktop/mobile artboard into the narrow handoff panel via CSS scale. */
function ScaledCodePreview({ url, device }: { url: string; device?: string }) {
  const { t } = useLanguage();
  const containerRef = useRef<HTMLDivElement>(null);
  const [panelW, setPanelW] = useState(300);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const sync = () => setPanelW(Math.max(160, el.clientWidth));
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const isApp = device === 'app' || device === 'mobile';
  const designW = isApp ? 390 : 1440;
  const designH = isApp ? 844 : 900;
  const scale = Math.min(1, panelW / designW);
  const scaledW = Math.round(designW * scale);
  const scaledH = Math.round(designH * scale);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <p className="min-w-0 text-[10px] leading-snug text-on-surface-variant">
          {t('Scaled to fit this panel')}
        </p>
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex shrink-0 items-center gap-1 text-[10px] font-semibold text-on-surface hover:underline"
        >
          <ExternalLink size={11} />
          {t('Open full size')}
        </a>
      </div>
      <div
        ref={containerRef}
        className="overflow-auto rounded-xl border border-outline-variant/30 bg-surface-container-low"
        style={{ maxHeight: 280 }}
      >
        <div className="relative mx-auto" style={{ width: scaledW, height: scaledH }}>
          <iframe
            title="preview"
            src={url}
            className="absolute left-0 top-0 border-0 bg-white"
            style={{
              width: designW,
              height: designH,
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
            }}
          />
        </div>
      </div>
    </div>
  );
}

/** D39 handoff as a 4-step flow: one primary action per screen + loading feedback. */
export function DesignHandoffTray({
  runId,
  session,
  busy,
  previewUrl,
  onClose,
  onSession,
  onPreviewUrl,
  onBusy,
  onSendToCoding,
}: Props) {
  const { t } = useLanguage();
  const gateStep = stepFromSession(session);
  const [viewStep, setViewStep] = useState<HandoffStep | null>(null);
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const step = viewStep && viewStep <= gateStep ? viewStep : gateStep;

  const run = async <T,>(action: BusyAction, fn: () => Promise<T>) => {
    setBusyAction(action);
    try {
      const result = await onBusy(fn);
      setViewStep(null);
      return result;
    } finally {
      setBusyAction(null);
    }
  };

  const stepCopy = useMemo(() => {
    switch (step) {
      case 1:
        return {
          title: t('Approve prototype'),
          body: t('Confirm the interactive prototype is ready before generating code.'),
        };
      case 2:
        return {
          title: t('Generate UI code'),
          body: t('Converts screens into a Vite + React + Tailwind app. Uses your active model and may take a minute.'),
        };
      case 3:
        return {
          title: t('Preview & approve'),
          body: t('Start a local preview, check the result, then approve the UI code.'),
        };
      default:
        return {
          title: t('Send to Coding'),
          body: t('Hand off DESIGN.md and the react/ scaffold to a Coding session.'),
        };
    }
  }, [step, t]);

  const isLoading = busy || busyAction !== null;

  return (
    <div className="absolute bottom-14 right-3 z-30 w-[340px] space-y-3 rounded-2xl border border-outline-variant/30 bg-white p-3.5 shadow-lg">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[12px] font-semibold text-on-surface">{t('UI code')}</p>
          <p className="text-[10px] text-on-surface-variant">
            {t('Step')} {step} / 4 · {t(STEP_LABELS[step - 1])}
          </p>
        </div>
        <button
          type="button"
          className="rounded-md p-1 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
          onClick={onClose}
          aria-label={t('Close')}
          disabled={busyAction === 'generate'}
        >
          <X size={14} />
        </button>
      </div>

      <ol className="flex items-center gap-1" aria-label={t('Handoff steps')}>
        {STEP_LABELS.map((label, i) => {
          const n = (i + 1) as HandoffStep;
          const done = n < gateStep;
          const current = n === step;
          const reachable = n <= gateStep;
          return (
            <li key={label} className="flex min-w-0 flex-1 items-center gap-1">
              <button
                type="button"
                disabled={!reachable || isLoading}
                onClick={() => setViewStep(n)}
                title={t(label)}
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-bold transition-colors ${
                  done
                    ? 'bg-emerald-600 text-white'
                    : current
                      ? 'bg-neutral-900 text-white'
                      : reachable
                        ? 'bg-surface-container-high text-on-surface'
                        : 'bg-surface-container text-on-surface-variant/50'
                }`}
                aria-current={current ? 'step' : undefined}
              >
                {done ? <Check size={12} /> : n}
              </button>
              {i < STEP_LABELS.length - 1 ? (
                <div
                  className={`h-px min-w-0 flex-1 ${done ? 'bg-emerald-500' : 'bg-outline-variant/40'}`}
                  aria-hidden
                />
              ) : null}
            </li>
          );
        })}
      </ol>

      <div className="space-y-1">
        <p className="text-[12px] font-semibold text-on-surface">{stepCopy.title}</p>
        <p className="text-[11px] leading-relaxed text-on-surface-variant">{stepCopy.body}</p>
      </div>

      {step === 1 ? (
        <button
          type="button"
          className={`${BTN_SUCCESS} w-full`}
          disabled={isLoading || !session?.screens?.length || Boolean(session?.prototype_approved)}
          onClick={() =>
            void run('approve', async () => {
              const next = await approveDesignPrototype(runId);
              onSession(next);
              return next;
            })
          }
        >
          {busyAction === 'approve' ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Check size={14} />
          )}
          {busyAction === 'approve' ? t('Working…') : t('Approve')}
        </button>
      ) : null}

      {step === 2 ? (
        <button
          type="button"
          className={`${BTN_PRIMARY} w-full`}
          disabled={isLoading || !session?.prototype_approved}
          onClick={() =>
            void run('generate', async () => {
              const next = await generateDesignReact(runId);
              onSession(next);
              return next;
            })
          }
        >
          {busyAction === 'generate' ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              {t('Generating UI code…')}
            </>
          ) : session?.react_ready ? (
            t('Regenerate UI code')
          ) : (
            t('Generate UI code')
          )}
        </button>
      ) : null}

      {step === 2 && busyAction === 'generate' ? (
        <p className="text-[10px] leading-relaxed text-on-surface-variant">
          {t('Converting each screen with your model — please keep this panel open.')}
        </p>
      ) : null}

      {step === 3 ? (
        <div className="space-y-2">
          <div className="flex gap-2">
            <button
              type="button"
              className={`${BTN_SECONDARY} flex-1`}
              disabled={isLoading || !session?.react_ready}
              onClick={() =>
                void run('preview', async () => {
                  const r = await startDesignPreview(runId);
                  onPreviewUrl(r.url);
                  return r;
                })
              }
            >
              {busyAction === 'preview' ? (
                <Loader2 size={14} className="animate-spin" />
              ) : null}
              {t('Start preview')}
            </button>
            <button
              type="button"
              className={`${BTN_SECONDARY} flex-1`}
              disabled={!previewUrl || isLoading}
              onClick={() =>
                void run('preview', async () => {
                  await stopDesignPreview(runId);
                  onPreviewUrl(null);
                })
              }
            >
              {t('Stop')}
            </button>
          </div>
          {previewUrl ? (
            <ScaledCodePreview url={previewUrl} device={session?.device} />
          ) : null}
          <button
            type="button"
            className={`${BTN_SUCCESS} w-full`}
            disabled={isLoading || !session?.react_ready || Boolean(session?.react_approved)}
            onClick={() =>
              void run('approve_react', async () => {
                const next = await approveDesignReact(runId);
                onSession(next);
                return next;
              })
            }
          >
            {busyAction === 'approve_react' ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Check size={14} />
            )}
            {busyAction === 'approve_react' ? t('Working…') : t('Approve UI code')}
          </button>
        </div>
      ) : null}

      {step === 4 ? (
        <button
          type="button"
          className={`${BTN_PRIMARY} w-full`}
          disabled={isLoading || !session?.react_approved}
          onClick={() =>
            void run('send', async () => {
              const handoff = await sendDesignToCoding(runId);
              onSendToCoding(handoff);
              return handoff;
            })
          }
        >
          {busyAction === 'send' ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              {t('Working…')}
            </>
          ) : (
            t('Send to Coding')
          )}
        </button>
      ) : null}
    </div>
  );
}
