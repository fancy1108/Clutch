import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  deleteProviderCredential,
  fetchModelsConfig,
  mapModelConfigToUi,
  PROVIDER_LABELS,
  rehydrateCcSwitchModels,
  saveModelsConfig,
  testModelConnection,
  type ProviderEntry,
} from '../services/modelsApi';

interface ModelItem {
  id: string;
  name: string;
  provider: string;
  providerId: string;
  contextWindow: string;
  temperature: number;
  description: string;
  credentialSourceLabel: string | null;
  credentialHint: string | null;
  endpoint: string | null;
  clutchManaged: boolean;
  isCcSwitch: boolean;
}

type VerifyState = 'idle' | 'testing' | 'ok' | 'failed';

interface ModelsManagerProps {
  activeModelId: string;
  setActiveModelId: (id: string) => void;
  selectedModel: string;
  setSelectedModel: (name: string) => void;
  configuredModels: ModelItem[];
  setConfiguredModels: React.Dispatch<React.SetStateAction<ModelItem[]>>;
}

const CONNECTABLE_PROVIDERS = ['deepseek', 'anthropic', 'openai', 'google', 'ollama', 'custom'] as const;

export const ModelsManager: React.FC<ModelsManagerProps> = ({
  activeModelId,
  setActiveModelId,
  selectedModel,
  setSelectedModel,
  configuredModels,
  setConfiguredModels,
}) => {
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const [providerId, setProviderId] = useState<string>('deepseek');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeAvailable, setActiveAvailable] = useState(true);
  const [providers, setProviders] = useState<Record<string, ProviderEntry>>({});
  const [verifyByModel, setVerifyByModel] = useState<Record<string, VerifyState>>({});
  const [verifyMessageByModel, setVerifyMessageByModel] = useState<Record<string, string>>({});
  const [verifyMessage, setVerifyMessage] = useState<string | null>(null);
  const [verifyOk, setVerifyOk] = useState<boolean | null>(null);
  const autoVerifiedRef = useRef(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const config = await fetchModelsConfig();
      const mapped = mapModelConfigToUi(config);
      setConfiguredModels(mapped.models);
      setProviders(mapped.providers);
      setActiveModelId(mapped.activeModelId);
      setActiveAvailable(mapped.activeAvailable);
      const active = mapped.models.find((m) => m.id === mapped.activeModelId);
      setSelectedModel(active?.name ?? '');
      return mapped.models;
    } catch {
      setConfiguredModels([]);
      setProviders({});
      setError('Sidecar unavailable — cannot load model configuration.');
      return [];
    } finally {
      setLoading(false);
    }
  }, [setActiveModelId, setConfiguredModels, setSelectedModel]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleTestConnection = useCallback(async (modelId: string) => {
    setVerifyByModel((prev) => ({ ...prev, [modelId]: 'testing' }));
    setVerifyMessage(null);
    setVerifyOk(null);
    setError(null);
    try {
      const result = await testModelConnection(modelId);
      if (result.ok) {
        setVerifyByModel((prev) => ({ ...prev, [modelId]: 'ok' }));
        setVerifyMessageByModel((prev) => ({ ...prev, [modelId]: result.message }));
        if (modelId === activeModelId) {
          setVerifyMessage(result.message);
          setVerifyOk(true);
        }
      } else {
        setVerifyByModel((prev) => ({ ...prev, [modelId]: 'failed' }));
        setVerifyMessageByModel((prev) => ({ ...prev, [modelId]: result.message }));
        if (modelId === activeModelId) {
          setVerifyMessage(result.message);
          setVerifyOk(false);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Connection test failed.';
      setVerifyByModel((prev) => ({ ...prev, [modelId]: 'failed' }));
      setVerifyMessageByModel((prev) => ({ ...prev, [modelId]: message }));
      if (modelId === activeModelId) {
        setVerifyMessage(message);
        setVerifyOk(false);
      }
    }
  }, [activeModelId]);

  useEffect(() => {
    if (autoVerifiedRef.current || configuredModels.length === 0 || loading) return;
    autoVerifiedRef.current = true;
    void Promise.all(configuredModels.map((model) => handleTestConnection(model.id)));
  }, [configuredModels, handleTestConnection, loading]);

  const openConnectForm = (provider?: string) => {
    setEditingProviderId(provider ?? null);
    setProviderId(provider ?? 'deepseek');
    setApiKey('');
    setShowApiKey(false);
    setShowConnectForm(true);
  };

  const handleActivate = async (modelId: string) => {
    setLoading(true);
    setError(null);
    try {
      await saveModelsConfig({ active_model_id: modelId });
      setVerifyByModel((prev) => ({ ...prev, [modelId]: 'idle' }));
      setVerifyMessage(null);
      setVerifyOk(null);
      autoVerifiedRef.current = false;
      const models = await refresh();
      const target = models.find((m) => m.id === modelId);
      if (target) void handleTestConnection(modelId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate model.');
      setLoading(false);
    }
  };

  const handleConnectProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await saveModelsConfig({ provider_id: providerId, api_key: apiKey.trim() });
      setApiKey('');
      setShowApiKey(false);
      setShowConnectForm(false);
      setEditingProviderId(null);
      setVerifyByModel({});
      setVerifyMessageByModel({});
      setVerifyMessage(null);
      setVerifyOk(null);
      autoVerifiedRef.current = false;
      const models = await refresh();
      await Promise.all(models.map((model) => handleTestConnection(model.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save provider credentials.');
      setLoading(false);
    }
  };

  const handleDeleteProvider = async (targetProviderId: string) => {
    const provider = providers[targetProviderId];
    const useCcSwitch = provider?.cc_switch_fallback_available;
    const message = useCcSwitch
      ? `Remove the Clutch-saved ${PROVIDER_LABELS[targetProviderId] ?? targetProviderId} key and use CC Switch credentials instead?`
      : `Remove the Clutch-saved API key for ${PROVIDER_LABELS[targetProviderId] ?? targetProviderId}?`;
    if (!window.confirm(message)) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await deleteProviderCredential(targetProviderId);
      setVerifyByModel({});
      setVerifyMessageByModel({});
      setVerifyMessage(null);
      setVerifyOk(null);
      autoVerifiedRef.current = false;
      const models = await refresh();
      if (models.length > 0) {
        await Promise.all(models.map((model) => handleTestConnection(model.id)));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove provider credentials.');
      setLoading(false);
    }
  };

  const handleRehydrateCcSwitch = async () => {
    setLoading(true);
    setError(null);
    try {
      await rehydrateCcSwitchModels();
      setVerifyByModel({});
      setVerifyMessageByModel({});
      setVerifyMessage(null);
      setVerifyOk(null);
      autoVerifiedRef.current = false;
      const models = await refresh();
      if (models.length > 0) {
        await Promise.all(models.map((model) => handleTestConnection(model.id)));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to sync CC Switch models.');
      setLoading(false);
    }
  };

  const managedProviders = CONNECTABLE_PROVIDERS.filter(
    (id) => providers[id]?.configured && providers[id]?.clutch_managed,
  );

  const activeVerify = activeModelId ? verifyByModel[activeModelId] ?? 'idle' : 'idle';

  const footerStatus = (() => {
    if (configuredModels.length === 0 || !activeAvailable) return 'No usable model';
    if (activeVerify === 'testing') return 'Testing connection…';
    if (activeVerify === 'ok') return 'Connection verified';
    if (activeVerify === 'failed') return 'Invalid credentials';
    return 'Checking…';
  })();

  const statusBadge = (verify: VerifyState) => {
    if (verify === 'testing') {
      return (
        <span className="text-[8.5px] uppercase font-mono bg-surface-container-high text-on-surface-variant border border-outline/60 px-1.5 py-0.2 rounded font-extrabold">
          Checking…
        </span>
      );
    }
    if (verify === 'ok') {
      return (
        <span className="text-[8.5px] uppercase font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.2 rounded font-extrabold">
          Valid
        </span>
      );
    }
    if (verify === 'failed') {
      return (
        <span className="text-[8.5px] uppercase font-mono bg-rose-50 text-rose-800 border border-rose-200 px-1.5 py-0.2 rounded font-extrabold">
          Invalid
        </span>
      );
    }
    return null;
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-surface-bright text-on-surface select-none leading-normal">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-on-surface">layers</span>
            <h2 className="text-base font-bold text-on-surface tracking-tight font-sans">AI Workspace Models</h2>
          </div>
          <p className="text-xs text-on-surface-variant font-sans leading-relaxed">
            Models appear when credentials are detected. Status is checked automatically — invalid keys show in red.
          </p>
        </div>

        {error && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">{error}</p>
        )}

        {verifyMessage && activeModelId && (
          <p
            className={`text-xs rounded-lg px-3 py-2 border ${
              verifyOk
                ? 'text-emerald-700 bg-emerald-50 border-emerald-100'
                : 'text-rose-700 bg-rose-50 border-rose-100'
            }`}
          >
            {verifyMessage}
          </p>
        )}

        {!activeAvailable && activeModelId && (
          <p className="text-xs text-rose-700 bg-rose-50 border border-rose-100 rounded-lg px-3 py-2">
            Active model is unavailable — connect provider credentials below.
          </p>
        )}

        {managedProviders.length > 0 && !showConnectForm && (
          <div className="space-y-2">
            <span className="text-[10px] font-extrabold text-on-surface-variant uppercase tracking-widest">
              Clutch-managed keys (built-in models only)
            </span>
            <p className="text-[10.5px] text-on-surface-variant">
              CC Switch imported models (e.g. Agnes) keep their own keys. Removing a key here restores CC Switch for built-in models.
            </p>
            <div className="grid grid-cols-1 gap-2">
              {managedProviders.map((id) => (
                <div
                  key={id}
                  className="flex items-center justify-between p-3 bg-surface-container border border-outline rounded-xl"
                >
                  <div className="text-left min-w-0">
                    <p className="text-xs font-bold text-on-surface">{PROVIDER_LABELS[id] ?? id}</p>
                    <p className="text-[10.5px] text-on-surface-variant truncate">
                      {providers[id]?.source_label ?? 'Clutch app storage (models.json)'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
                    {providers[id]?.cc_switch_fallback_available && (
                      <button
                        type="button"
                        onClick={() => void handleDeleteProvider(id)}
                        className="px-3 py-1.5 text-[10.5px] font-bold border border-primary/40 text-primary rounded-lg hover:bg-primary/5"
                      >
                        Use CC Switch
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => openConnectForm(id)}
                      className="px-3 py-1.5 text-[10.5px] font-bold border border-outline rounded-lg hover:bg-surface-container-high"
                    >
                      Update key
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteProvider(id)}
                      className="px-3 py-1.5 text-[10.5px] font-bold border border-rose-200 text-rose-700 rounded-lg hover:bg-rose-50"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!showConnectForm && (
          <div className="flex items-center justify-between p-3 bg-surface-container border border-outline rounded-xl">
            <div className="text-left">
              <h3 className="text-xs font-bold text-on-surface">CC Switch models</h3>
              <p className="text-[10.5px] text-on-surface-variant">Re-import providers and keys from ~/.cc-switch without restarting.</p>
            </div>
            <button
              type="button"
              disabled={loading}
              onClick={() => void handleRehydrateCcSwitch()}
              className="px-3.5 py-1.5 rounded-lg text-xs font-bold border border-outline hover:bg-surface-container-high disabled:opacity-50"
            >
              Sync from CC Switch
            </button>
          </div>
        )}

        {showConnectForm ? (
          <form onSubmit={(e) => void handleConnectProvider(e)} className="p-4 bg-surface-container border border-outline rounded-xl space-y-4 text-left">
            <h3 className="text-xs font-bold text-on-surface">
              {editingProviderId ? 'Update Provider API Key' : 'Connect Provider API Key'}
            </h3>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">Provider</label>
              <select
                value={providerId}
                onChange={(e) => setProviderId(e.target.value)}
                disabled={Boolean(editingProviderId)}
                className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface disabled:opacity-60"
              >
                {CONNECTABLE_PROVIDERS.map((id) => (
                  <option key={id} value={id}>
                    {PROVIDER_LABELS[id] ?? id}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">API Key</label>
              <div className="relative flex items-center">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  required
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-••••••••"
                  className="w-full text-xs border border-outline bg-surface rounded-lg pl-3 pr-10 py-2 font-mono text-on-surface"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="absolute right-3 text-on-surface-variant hover:text-on-surface flex items-center"
                >
                  <span className="material-symbols-outlined text-[18px]">
                    {showApiKey ? 'visibility' : 'visibility_off'}
                  </span>
                </button>
              </div>
              <p className="text-[10px] text-on-surface-variant">
                Gateway models (Agnes, etc.) use tokens from that gateway — not api.anthropic.com keys.
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowConnectForm(false);
                  setShowApiKey(false);
                  setEditingProviderId(null);
                }}
                className="px-3 py-1.5 text-xs font-bold border border-outline rounded-lg"
              >
                Cancel
              </button>
              <button type="submit" disabled={loading} className="px-4 py-1.5 text-xs font-bold bg-primary text-on-primary rounded-lg disabled:opacity-50">
                Save credentials
              </button>
            </div>
          </form>
        ) : (
          <div className="flex items-center justify-between p-3.5 bg-surface-container border border-outline rounded-xl">
            <div className="text-left">
              <h3 className="text-xs font-bold text-on-surface">Connect a provider</h3>
              <p className="text-[10.5px] text-on-surface-variant">Add or replace an API key for a provider.</p>
            </div>
            <button type="button" onClick={() => openConnectForm()} className="bg-primary text-on-primary px-3.5 py-1.5 rounded-lg text-xs font-bold">
              Add API Key
            </button>
          </div>
        )}

        <div className="space-y-3 text-left">
          <div className="flex items-center justify-between pb-1 border-b border-outline/40">
            <span className="text-[10px] font-extrabold text-on-surface-variant uppercase tracking-widest">Available Models</span>
            <span className="text-[10px] font-mono text-on-surface-variant">{configuredModels.length} with credentials</span>
          </div>

          {loading && configuredModels.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-4">Loading…</p>
          ) : configuredModels.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-4">
              No models available. Connect a provider API key above — only then can you activate a model.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-2.5">
              {configuredModels.map((model) => {
                const isActive = activeModelId === model.id;
                const verify = verifyByModel[model.id] ?? 'idle';
                const rowMessage = verifyMessageByModel[model.id];
                return (
                  <div
                    key={model.id}
                    className={`relative p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                      isActive ? 'bg-surface-container border-primary shadow-xs' : 'bg-surface border-outline/65'
                    }`}
                  >
                    <div className="flex-1 space-y-1.5 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold text-on-surface truncate">{model.name}</span>
                        <span className="text-[8.5px] uppercase font-mono bg-surface-container-high text-on-surface-variant border border-outline/60 px-1.5 py-0.2 rounded font-extrabold">
                          {model.provider}
                        </span>
                        {model.isCcSwitch && (
                          <span className="text-[8.5px] uppercase font-mono bg-sky-50 text-sky-800 border border-sky-200 px-1.5 py-0.2 rounded font-extrabold">
                            CC Switch
                          </span>
                        )}
                          <span className="text-[8.5px] uppercase font-mono bg-primary/10 text-primary border border-primary/30 px-1.5 py-0.2 rounded font-extrabold">
                            Active
                          </span>
                        )}
                        {statusBadge(verify)}
                      </div>
                      <p className="text-[11.5px] text-on-surface-variant">{model.description}</p>
                      {model.endpoint && (
                        <p className="text-[10.5px] text-on-surface-variant font-mono truncate">Endpoint: {model.endpoint}</p>
                      )}
                      {model.credentialHint && (
                        <p className="text-[10.5px] text-amber-800 bg-amber-50 border border-amber-100 rounded-md px-2 py-1">
                          {model.credentialHint}
                        </p>
                      )}
                      {verify === 'failed' && rowMessage && (
                        <p className="text-[10.5px] text-rose-700">{rowMessage}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 justify-end flex-shrink-0 flex-wrap">
                      <button
                        type="button"
                        disabled={loading || verify === 'testing'}
                        onClick={() => void handleTestConnection(model.id)}
                        className="bg-surface-container hover:bg-surface-container-high border border-outline text-on-surface px-3 py-1.5 rounded-lg text-[10.5px] font-bold disabled:opacity-50"
                      >
                        {verify === 'testing' ? 'Testing…' : 'Retest'}
                      </button>
                      {isActive ? (
                        <span className="material-symbols-outlined text-[20px] text-on-primary bg-primary p-1.5 rounded-full border border-outline/50">
                          check
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled={loading || verify === 'failed'}
                          onClick={() => void handleActivate(model.id)}
                          className="bg-surface-container hover:bg-primary hover:text-on-primary border border-outline text-on-surface px-3 py-1.5 rounded-lg text-[10.5px] font-bold disabled:opacity-50"
                          title={verify === 'failed' ? 'Fix credentials before activating' : undefined}
                        >
                          Activate
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="h-10 bg-surface-container border-t border-outline flex items-center justify-between px-6 text-[10px] text-on-surface-variant">
        <div className="flex items-center gap-1 font-mono font-bold uppercase tracking-wide">
          <span>Active model:</span>
          <span className="text-on-surface font-extrabold">{selectedModel || '—'}</span>
        </div>
        <div className="flex items-center gap-3">
          {activeModelId && activeAvailable && (
            <button
              type="button"
              disabled={activeVerify === 'testing'}
              onClick={() => void handleTestConnection(activeModelId)}
              className="text-[9.5px] font-bold text-on-surface-variant hover:text-on-surface disabled:opacity-50"
            >
              Retest active
            </button>
          )}
          <span
            className={`font-mono text-[9.5px] ${
              activeVerify === 'ok'
                ? 'text-emerald-700'
                : activeVerify === 'failed'
                  ? 'text-rose-700'
                  : ''
            }`}
          >
            {footerStatus}
          </span>
        </div>
      </div>
    </div>
  );
};
