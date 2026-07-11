import React, { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useLanguage } from './LanguageContext';
import { BTN_GHOST_SM, BTN_PRIMARY_SM } from './ui/buttonStyles';
import { BADGE_NEUTRAL } from './ui/surfaceStyles';
import {
  applySidecarPatch,
  checkAndDownloadSidecarPatch,
  shouldCheckSidecarPatch,
} from '../services/sidecarPatch';
import { isHotpatchSuppressed } from '../services/appUpdater';

/**
 * Silent sidecar hotpatch ready chip (D37).
 * Hidden while a full app UpdateBanner is active.
 */
export const SidecarPatchReady: React.FC = () => {
  const { t } = useLanguage();
  const [patchId, setPatchId] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [suppressed, setSuppressed] = useState(false);

  useEffect(() => {
    if (!shouldCheckSidecarPatch()) return;

    let cancelled = false;
    const timer = window.setTimeout(() => {
      if (isHotpatchSuppressed()) {
        setSuppressed(true);
        return;
      }
      void checkAndDownloadSidecarPatch()
        .then((id) => {
          if (cancelled || !id || isHotpatchSuppressed()) return;
          setPatchId(id);
        })
        .catch((err) => {
          console.warn('[Clutch] Sidecar patch check failed:', err);
        });
    }, 5500);

    const poll = window.setInterval(() => {
      const next = isHotpatchSuppressed();
      setSuppressed(next);
    }, 1000);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      window.clearInterval(poll);
    };
  }, []);

  const handleApply = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    try {
      await applySidecarPatch();
      setPatchId(null);
      setConfirmOpen(false);
    } catch (err) {
      console.warn('[Clutch] Sidecar patch apply failed:', err);
    } finally {
      setBusy(false);
    }
  }, [busy]);

  if (!patchId || suppressed) return null;

  return (
    <>
      <button
        type="button"
        data-testid="sidecar-patch-ready"
        onClick={() => setConfirmOpen(true)}
        className={`${BADGE_NEUTRAL} inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-neutral-200/80 hover:bg-neutral-200/60 transition-colors cursor-pointer`}
        title={t('Runtime update ready')}
        aria-label={t('Runtime update ready')}
      >
        {t('Update ready')}
      </button>

      {confirmOpen && (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/30 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="sidecar-patch-title"
        >
          <div className="w-full max-w-sm rounded-[24px] bg-surface-container-low border border-outline-variant/40 shadow-xl p-5 space-y-4">
            <h2 id="sidecar-patch-title" className="text-sm font-semibold text-on-surface">
              {t('Runtime update ready')}
            </h2>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              {t(
                'A runtime update is ready. Apply now? The orchestrator will restart briefly; the current chat may be interrupted.',
              )}
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                className={BTN_GHOST_SM}
                disabled={busy}
                onClick={() => setConfirmOpen(false)}
              >
                {t('Later')}
              </button>
              <button
                type="button"
                className={BTN_PRIMARY_SM}
                disabled={busy}
                onClick={() => {
                  void handleApply();
                }}
              >
                {busy ? <Loader2 className="size-3 animate-spin" aria-hidden /> : null}
                {t('Apply')}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
