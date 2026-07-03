import React, { useState } from 'react';
import { BTN_GHOST, BTN_PRIMARY } from './ui/buttonStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { useLanguage } from './LanguageContext';
import { CliScanNotice, CliScanRescanButton } from './CliScanNotice';
import { CcSwitchCliSetupBanner } from './CcSwitchCliSetupBanner';
import { useCliModelsScan } from '../hooks/useCliModelsScan';
import {
  activateCliModel,
  activateCliProvider,
} from '../services/cliConfigApi';

function modelRefForItem(item: { model_ref?: string; provider: string; model_id: string }): string {
  return item.model_ref ?? `${item.provider}/${item.model_id}`;
}

export const OpenCodeModelsPanel: React.FC = () => {
  const { t } = useLanguage();
  const { data, loading, error, notice, dismissNotice, refresh, refreshSilent } =
    useCliModelsScan('opencode-cli');
  const [activatingRef, setActivatingRef] = useState<string | null>(null);
  const [activatingProviderId, setActivatingProviderId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleActivateModel = async (modelRef: string) => {
    setActivatingRef(modelRef);
    setMessage(null);
    try {
      const result = await activateCliModel('opencode-cli', modelRef);
      setMessage(result.message);
      await refreshSilent();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t('Failed to switch model.'));
    } finally {
      setActivatingRef(null);
    }
  };

  const handleActivateProvider = async (providerId: string) => {
    setActivatingProviderId(providerId);
    setMessage(null);
    try {
      const result = await activateCliProvider('opencode-cli', providerId);
      setMessage(result.message);
      await refreshSilent();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t('Failed to switch provider.'));
    } finally {
      setActivatingProviderId(null);
    }
  };

  const activeModel = data?.active_model_id ?? null;
  const canSwitchModels = data?.opencode_cli_available !== false;

  return (
    <div className="space-y-4 text-left">
      <p className="text-xs text-on-surface-variant leading-relaxed">
        {t('Models used by the OpenCode CLI (opencode run). This is separate from OpenCode Zen models configured for the Clutch built-in agent.')}
      </p>

      <div className="space-y-2">
        <div className="flex gap-2">
          <CliScanRescanButton loading={loading} onClick={() => void refresh()} />
          <a
            href="https://dev.opencode.ai/docs/config/"
            target="_blank"
            rel="noreferrer"
            className={`${BTN_GHOST} text-[10.5px] inline-flex items-center gap-1`}
          >
            <LegacyIcon name="open_in_new" className="text-[13px]" />
            {t('OpenCode config docs')}
          </a>
        </div>
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
            <p className="text-sm font-mono text-neutral-900">{activeModel ?? t('Not detected')}</p>
            {data.default_agent ? (
              <p className="text-[10px] text-neutral-500">{t('Default agent')}: {String(data.default_agent)}</p>
            ) : null}
            {data.config_paths && data.config_paths.length > 0 ? (
              <p className="text-[10px] text-neutral-500 break-all">
                {t('Config')}: {data.config_paths.join(', ')}
              </p>
            ) : (
              <p className="text-[10px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-2">
                {t('No opencode.json found. Run opencode once or create ~/.config/opencode/opencode.json.')}
              </p>
            )}
            {data.auth_path ? (
              <p className="text-[10px] text-neutral-500 break-all">{t('Credentials')}: {data.auth_path}</p>
            ) : null}
          </section>

          {data.auth_providers && data.auth_providers.length > 0 ? (
            <section className="space-y-2">
              <h3 className="text-[11px] font-bold uppercase tracking-wide text-neutral-600">
                {t('Configured credentials')}
              </h3>
              <div className="space-y-1.5">
                {data.auth_providers.map((provider) => (
                  <div
                    key={provider.id}
                    className="p-2.5 rounded-lg border border-neutral-200 bg-white text-[10px] flex items-center justify-between gap-2"
                  >
                    <div>
                      <div className="font-bold text-neutral-900">{provider.name}</div>
                      <div className="text-neutral-500 mt-0.5">{provider.auth_type}</div>
                    </div>
                    <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                      {t('Connected')}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {data.catalog && data.catalog.length > 0 ? (
            <section className="space-y-2">
              <h3 className="text-[11px] font-bold uppercase tracking-wide text-neutral-600">
                {t('Available models')}
              </h3>
              <p className="text-[10px] text-neutral-500 leading-relaxed">
                {canSwitchModels
                  ? t('Select a model to set the OpenCode CLI default. Free built-in models are included.')
                  : t('Install the opencode CLI on PATH to switch models from Clutch.')}
              </p>
              <div className="space-y-1.5">
                {data.catalog.map((item) => {
                  const modelRef = modelRefForItem(item);
                  const isActive = activeModel === modelRef || activeModel === item.model_id;
                  return (
                    <div
                      key={modelRef}
                      className="flex items-start justify-between gap-3 p-3 rounded-xl border border-neutral-200 bg-white"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <div className="text-xs font-bold text-neutral-900 truncate">{item.name}</div>
                          {item.is_builtin ? (
                            <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-sky-100 text-sky-800">
                              {t('Free')}
                            </span>
                          ) : null}
                        </div>
                        <div className="text-[10px] text-neutral-500 font-mono mt-0.5 truncate">{modelRef}</div>
                        {isActive ? (
                          <span className="inline-block mt-1 text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                            {t('In use')}
                          </span>
                        ) : null}
                      </div>
                      {!isActive && canSwitchModels ? (
                        <button
                          type="button"
                          disabled={activatingRef === modelRef}
                          onClick={() => void handleActivateModel(modelRef)}
                          className={`${BTN_PRIMARY} text-[10px] shrink-0 disabled:opacity-50`}
                        >
                          {activatingRef === modelRef ? t('Switching…') : t('Use model')}
                        </button>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </section>
          ) : null}

          {data.providers.length > 0 ? (
            <section className="space-y-2">
              <h3 className="text-[11px] font-bold uppercase tracking-wide text-neutral-600">
                {t('CC Switch providers')}
              </h3>
              {!data.cc_switch_cli_available && data.cc_switch_found ? (
                <CcSwitchCliSetupBanner
                  message={t('CC Switch app data detected. Install the cc-switch CLI on PATH to switch providers from Clutch, or switch in the CC Switch desktop app.')}
                  onInstalled={() => void refreshSilent()}
                />
              ) : null}
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
                        disabled={activatingProviderId === provider.id}
                        onClick={() => void handleActivateProvider(provider.id)}
                        className={`${BTN_PRIMARY} text-[10px] shrink-0 disabled:opacity-50`}
                      >
                        {activatingProviderId === provider.id ? t('Switching…') : t('Activate')}
                      </button>
                    ) : null}
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
};
