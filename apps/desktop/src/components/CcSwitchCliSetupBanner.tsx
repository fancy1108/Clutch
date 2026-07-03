import React, { useEffect, useState } from 'react';
import { BTN_PRIMARY } from './ui/buttonStyles';
import { useLanguage } from './LanguageContext';
import { installCcSwitchCli, prefetchCcSwitchCli } from '../services/cliConfigApi';

type CcSwitchCliSetupBannerProps = {
  message: string;
  onInstalled?: () => void | Promise<void>;
};

export const CcSwitchCliSetupBanner: React.FC<CcSwitchCliSetupBannerProps> = ({
  message,
  onInstalled,
}) => {
  const { t } = useLanguage();
  const [installing, setInstalling] = useState(false);
  const [installError, setInstallError] = useState<string | null>(null);
  const [installSuccess, setInstallSuccess] = useState<string | null>(null);
  const [bundleReady, setBundleReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void prefetchCcSwitchCli()
      .then((result) => {
        if (!cancelled && result.ok) {
          setBundleReady(true);
        }
      })
      .catch(() => {
        // Prefetch is best-effort; install will retry download if needed.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleInstall = async () => {
    setInstalling(true);
    setInstallError(null);
    setInstallSuccess(null);
    try {
      const result = await installCcSwitchCli();
      setInstallSuccess(result.message);
      await onInstalled?.();
    } catch (err) {
      setInstallError(err instanceof Error ? err.message : t('Failed to install cc-switch CLI.'));
    } finally {
      setInstalling(false);
    }
  };

  if (installSuccess) {
    return (
      <p className="text-[10px] text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-2.5 py-2 leading-relaxed">
        {installSuccess}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 text-[10px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-2">
        <div className="flex-1 space-y-1">
          <p className="leading-relaxed">{message}</p>
          {bundleReady ? (
            <p className="text-emerald-700">{t('Install package is ready — click to finish setup.')}</p>
          ) : null}
        </div>
        <button
          type="button"
          disabled={installing}
          onClick={() => void handleInstall()}
          className={`${BTN_PRIMARY} text-[10px] shrink-0 disabled:opacity-50 whitespace-nowrap`}
        >
          {installing ? t('Installing…') : t('Set up cc-switch CLI')}
        </button>
      </div>
      {installError ? (
        <p className="text-[10px] text-rose-800 bg-rose-50 border border-rose-100 rounded-lg px-2.5 py-2">
          {installError}
        </p>
      ) : null}
    </div>
  );
};
