import React, { useState } from 'react';
import { BTN_PRIMARY } from './ui/buttonStyles';
import { useLanguage } from './LanguageContext';
import { CliScanNotice, CliScanRescanButton } from './CliScanNotice';
import { CcSwitchCliSetupBanner } from './CcSwitchCliSetupBanner';
import { useCliModelsScan } from '../hooks/useCliModelsScan';
import { activateCliProvider } from '../services/cliConfigApi';

export const ClaudeCodeModelsPanel: React.FC = () => {
  const { t } = useLanguage();
  const { data, loading, error, notice, dismissNotice, refresh, refreshSilent } =
    useCliModelsScan('claude-cli');
  const [activatingId, setActivatingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleActivate = async (providerId: string) => {
    setActivatingId(providerId);
    setMessage(null);
    try {
      const result = await activateCliProvider('claude-cli', providerId);
      setMessage(result.message);
      await refreshSilent();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t('Failed to switch provider.'));
    } finally {
      setActivatingId(null);
    }
  };

  const ccSwitchHint = (() => {
    if (!data || data.cc_switch_cli_available) return null;
    if (data.cc_switch_found) {
      return t('CC Switch app data detected. Install the cc-switch CLI on PATH to switch providers from Clutch, or switch in the CC Switch desktop app.');
    }
    return t('Install the cc-switch CLI on PATH to switch providers from Clutch, or use the CC Switch desktop app.');
  })();

  return (
    <div className="space-y-4 text-left">
      <p className="text-xs text-on-surface-variant leading-relaxed">
        {t('Models used by the Claude Code CLI subprocess. Clutch does not inject Models Manager settings into Claude agents.')}
      </p>
      <p className="text-[10px] text-neutral-500 leading-relaxed">
        {t('Claude Code provider switching uses CC Switch. OpenCode uses its own native config and does not require cc-switch CLI.')}
      </p>

      <div className="space-y-2">
        <CliScanRescanButton loading={loading} onClick={() => void refresh()} />
        <CliScanNotice notice={notice} onDismiss={dismissNotice} />
      </div>

      {error ? (
        <p className="text-xs text-rose-800 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2">{error}</p>
      ) : null}
      {message ? (
        <p className="text-xs text-neutral-700 bg-neutral-50 border border-neutral-200 rounded-xl px-3 py-2">{message}</p>
      ) : null}

      {data ? (
        <>
          <section className="rounded-xl border border-outline-variant bg-surface-container-lowest p-4 space-y-2">
            <h3 className="text-[11px] font-bold uppercase tracking-wide text-neutral-600">{t('Current model')}</h3>
            <p className="text-sm font-mono text-neutral-900">{data.active_model_id ?? t('Not detected')}</p>
            {data.base_url ? (
              <p className="text-[10px] text-neutral-500 break-all">{t('Base URL')}: {data.base_url}</p>
            ) : null}
            <p className="text-[10px] text-neutral-500">
              {data.cc_switch_found ? t('CC Switch database detected') : t('CC Switch not found — showing ~/.claude/settings.json only')}
            </p>
            {ccSwitchHint && !data.cc_switch_cli_available ? (
              <CcSwitchCliSetupBanner message={ccSwitchHint} onInstalled={() => void refreshSilent()} />
            ) : null}
            {data.cc_switch_cli_available ? (
              <p className="text-[10px] text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-2.5 py-2">
                {t('cc-switch CLI detected — you can switch providers below.')}
              </p>
            ) : null}
          </section>

          {data.providers.length > 0 ? (
            <section className="space-y-2">
              <h3 className="text-[11px] font-bold uppercase tracking-wide text-neutral-600">
                {t('CC Switch providers')}
              </h3>
              <p className="text-[10px] text-neutral-500 leading-relaxed">
                {data.cc_switch_cli_available
                  ? t('Activate a provider to change the Claude Code CLI model.')
                  : t('Read-only list. Switch providers in CC Switch or install cc-switch CLI for in-app switching.')}
              </p>
              <div className="space-y-2">
                {data.providers.map((provider) => (
                  <div
                    key={provider.id}
                    className="flex items-start justify-between gap-3 p-3 rounded-xl border border-neutral-200 bg-white"
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-neutral-900 truncate">{provider.name}</div>
                      <div className="text-[10px] text-neutral-500 font-mono mt-0.5 truncate">
                        {provider.model_id ?? t('No model id')}
                      </div>
                      {provider.is_active ? (
                        <span className="inline-block mt-1 text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                          {t('In use')}
                        </span>
                      ) : null}
                    </div>
                    {!provider.is_active && data.cc_switch_cli_available ? (
                      <button
                        type="button"
                        disabled={activatingId === provider.id}
                        onClick={() => void handleActivate(provider.id)}
                        className={`${BTN_PRIMARY} text-[10px] shrink-0 disabled:opacity-50`}
                      >
                        {activatingId === provider.id ? t('Switching…') : t('Activate')}
                      </button>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {data.env_preview && Object.keys(data.env_preview).length > 0 ? (
            <section className="rounded-xl border border-neutral-200 bg-neutral-50/80 p-3">
              <h3 className="text-[10px] font-bold uppercase tracking-wide text-neutral-500 mb-2">
                {t('Claude settings preview')}
              </h3>
              <dl className="space-y-1">
                {Object.entries(data.env_preview).map(([key, value]) => (
                  <div key={key} className="grid grid-cols-[1fr_auto] gap-2 text-[10px] font-mono">
                    <dt className="text-neutral-500 truncate">{key}</dt>
                    <dd className="text-neutral-800 truncate">{value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
};
