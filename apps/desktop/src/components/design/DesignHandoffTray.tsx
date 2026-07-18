import React from 'react';
import { Check, X } from 'lucide-react';
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

/** Secondary tray: Approve Prototype → React → Vite preview → Approve → Send to Coding (D39). */
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

  return (
    <div className="absolute right-4 top-4 z-20 w-[300px] space-y-2 rounded-2xl border border-outline-variant/30 bg-white p-3 shadow-md">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[12px] font-semibold text-on-surface">{t('UI code')}</p>
          <p className="text-[10px] text-on-surface-variant">
            {t('Prototype → Approve → UI code → Coding')}
          </p>
        </div>
        <button
          type="button"
          className="rounded-md p-1 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
          onClick={onClose}
          aria-label={t('Close')}
        >
          <X size={14} />
        </button>
      </div>
      <p className="text-[11px] leading-relaxed text-on-surface-variant">
        {session?.prototype_approved
          ? t('Prototype approved. Generate a Vite + React + Tailwind app.')
          : t('Approve the prototype first.')}
      </p>
      <button
        type="button"
        className={`${BTN_SUCCESS} w-full`}
        disabled={busy || !session?.screens?.length || Boolean(session?.prototype_approved)}
        onClick={() =>
          void onBusy(async () => {
            const next = await approveDesignPrototype(runId);
            onSession(next);
            return next;
          })
        }
      >
        <Check size={14} /> {t('Approve')}
      </button>
      <button
        type="button"
        className={`${BTN_PRIMARY} w-full`}
        disabled={busy || !session?.prototype_approved}
        onClick={() =>
          void onBusy(async () => {
            const next = await generateDesignReact(runId);
            onSession(next);
            return next;
          })
        }
      >
        {t('Generate UI code')}
      </button>
      <div className="flex gap-2">
        <button
          type="button"
          className={`${BTN_SECONDARY} flex-1`}
          disabled={busy || !session?.react_ready}
          onClick={() =>
            void onBusy(async () => {
              const r = await startDesignPreview(runId);
              onPreviewUrl(r.url);
              return r;
            })
          }
        >
          {t('Start preview')}
        </button>
        <button
          type="button"
          className={`${BTN_SECONDARY} flex-1`}
          disabled={!previewUrl}
          onClick={() =>
            void onBusy(async () => {
              await stopDesignPreview(runId);
              onPreviewUrl(null);
            })
          }
        >
          {t('Stop')}
        </button>
      </div>
      {previewUrl ? (
        <iframe
          title="preview"
          src={previewUrl}
          className="h-40 w-full rounded-xl border border-outline-variant/30"
        />
      ) : null}
      <button
        type="button"
        className={`${BTN_SUCCESS} w-full`}
        disabled={busy || !session?.react_ready || Boolean(session?.react_approved)}
        onClick={() =>
          void onBusy(async () => {
            const next = await approveDesignReact(runId);
            onSession(next);
            return next;
          })
        }
      >
        {t('Approve UI code')}
      </button>
      <button
        type="button"
        className={`${BTN_PRIMARY} w-full`}
        disabled={busy || !session?.react_approved}
        onClick={() =>
          void onBusy(async () => {
            const handoff = await sendDesignToCoding(runId);
            onSendToCoding(handoff);
            return handoff;
          })
        }
      >
        {t('Send to Coding')}
      </button>
    </div>
  );
}
