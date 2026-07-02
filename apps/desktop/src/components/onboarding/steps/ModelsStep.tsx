import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Eye, EyeOff, Loader2 } from 'lucide-react';

import { useLanguage } from '../../LanguageContext';
import {
  fetchModelsConfig,
  mapModelConfigToUi,
  ModelsConfigError,
  PROVIDER_LABELS,
  saveModelsConfig,
  testModelConnection,
} from '../../../services/modelsApi';
import { BTN_GHOST, BTN_PRIMARY } from '../../ui/buttonStyles';

const CONNECTABLE_PROVIDERS = ['deepseek', 'anthropic', 'openai', 'google', 'ollama', 'custom'] as const;
const KEYLESS_PROVIDERS = new Set(['ollama']);

interface ModelsStepProps {
  modelReady: boolean;
  onModelReady: (ready: boolean) => void;
  onSkip: () => void;
}

export function ModelsStep({ modelReady, onModelReady, onSkip }: ModelsStepProps) {
  const { t } = useLanguage();
  const [providerId, setProviderId] = useState<string>('deepseek');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshModels = useCallback(async () => {
    try {
      const config = await fetchModelsConfig();
      const mapped = mapModelConfigToUi(config);
      const active = mapped.models.find((m) => m.id === mapped.activeModelId);
      if (active?.available && KEYLESS_PROVIDERS.has(active.providerId)) {
        onModelReady(true);
      }
      return mapped;
    } catch (err) {
      if (err instanceof ModelsConfigError && err.kind === 'server') {
        setError(t('Sidecar backend error — quit Clutch (Cmd+Q) and reopen the app.'));
      } else if (err instanceof ModelsConfigError && err.kind === 'unauthorized') {
        setError(t('Sidecar session expired — quit Clutch (Cmd+Q) and reopen the app.'));
      } else {
        setError(t('Cannot reach Clutch sidecar'));
      }
      return null;
    }
  }, [onModelReady, t]);

  useEffect(() => {
    void refreshModels();
  }, [refreshModels]);

  const handleSaveAndTest = async () => {
    if (!KEYLESS_PROVIDERS.has(providerId) && !apiKey.trim()) {
      setError(t('Enter an API key for this provider'));
      return;
    }
    setSaving(true);
    setError(null);
    setTestMessage(null);
    try {
      await saveModelsConfig({
        provider_id: providerId,
        api_key: apiKey.trim() || undefined,
      });
      const mapped = await refreshModels();
      const target = mapped?.models.find((m) => m.providerId === providerId && m.available)
        ?? mapped?.models.find((m) => m.id === mapped.activeModelId);
      if (!target) {
        setError(t('No model available for this provider yet'));
        return;
      }
      setTesting(true);
      const result = await testModelConnection(target.id);
      setTestMessage(t(result.message));
      if (result.ok) {
        onModelReady(true);
      } else {
        onModelReady(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Could not save model configuration'));
      onModelReady(false);
    } finally {
      setSaving(false);
      setTesting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="text-center">
        <h2 className="text-xl font-bold text-neutral-900">{t('Connect a cloud model')}</h2>
        <p className="mt-2 text-sm text-neutral-500 max-w-md mx-auto">
          {t('Onboarding models skip hint')}
        </p>
      </div>

      <div className="space-y-3 max-w-md mx-auto">
        <label className="block text-left">
          <span className="text-[10px] font-bold uppercase tracking-wide text-neutral-500">
            {t('Provider Platform')}
          </span>
          <select
            data-testid="onboarding-model-provider"
            value={providerId}
            onChange={(e) => setProviderId(e.target.value)}
            className="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 pr-8 text-sm text-neutral-900"
          >
            {CONNECTABLE_PROVIDERS.map((id) => (
              <option key={id} value={id}>
                {PROVIDER_LABELS[id] ?? id}
              </option>
            ))}
          </select>
        </label>

        {!KEYLESS_PROVIDERS.has(providerId) && (
          <label className="block text-left">
            <span className="text-[10px] font-bold uppercase tracking-wide text-neutral-500">
              {t('API Key / Credentials (Optional)')}
            </span>
            <div className="mt-1 relative">
              <input
                data-testid="onboarding-model-api-key"
                type={showApiKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 pr-10 text-sm"
                placeholder="sk-…"
              />
              <button
                type="button"
                onClick={() => setShowApiKey((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400"
                aria-label={showApiKey ? t('Hide') : t('Show')}
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </label>
        )}

        <p className="text-[10px] text-neutral-500 text-left">{t('Onboarding keychain note')}</p>

        {modelReady && (
          <p className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
            <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
            {testMessage ?? t('Model connection verified')}
          </p>
        )}

        {error && (
          <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex gap-2 pt-1">
          <button
            type="button"
            data-testid="onboarding-model-test"
            disabled={saving || testing}
            onClick={() => void handleSaveAndTest()}
            className={`${BTN_PRIMARY} flex-1 flex items-center justify-center gap-2`}
          >
            {(saving || testing) && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('Test connection')}
          </button>
          <button type="button" data-testid="onboarding-model-skip" onClick={onSkip} className={BTN_GHOST}>
            {t('Skip for now')}
          </button>
        </div>
      </div>
    </div>
  );
}
