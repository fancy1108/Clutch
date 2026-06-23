import React, { useCallback, useEffect, useState } from 'react';
import {
  fetchModelsConfig,
  mapModelConfigToUi,
  PROVIDER_LABELS,
  saveModelsConfig,
  testModelConnection,
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
  const [providerId, setProviderId] = useState<string>('deepseek');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeAvailable, setActiveAvailable] = useState(true);
  const [verifyByModel, setVerifyByModel] = useState<Record<string, VerifyState>>({});
  const [verifyMessage, setVerifyMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const config = await fetchModelsConfig();
      const mapped = mapModelConfigToUi(config);
      setConfiguredModels(mapped.models);
      setActiveModelId(mapped.activeModelId);
      setActiveAvailable(mapped.activeAvailable);
      const active = mapped.models.find((m) => m.id === mapped.activeModelId);
      setSelectedModel(active?.name ?? '');
    } catch {
      setConfiguredModels([]);
      setError('Sidecar unavailable — cannot load model configuration.');
    } finally {
      setLoading(false);
    }
  }, [setActiveModelId, setConfiguredModels, setSelectedModel]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleActivate = async (modelId: string) => {
    setLoading(true);
    setError(null);
    try {
      await saveModelsConfig({ active_model_id: modelId });
      setVerifyByModel((prev) => ({ ...prev, [modelId]: 'idle' }));
      setVerifyMessage(null);
      await refresh();
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
      setShowConnectForm(false);
      setVerifyByModel({});
      setVerifyMessage(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save provider credentials.');
      setLoading(false);
    }
  };

  const handleTestConnection = async (modelId: string) => {
    setVerifyByModel((prev) => ({ ...prev, [modelId]: 'testing' }));
    setVerifyMessage(null);
    setError(null);
    try {
      const result = await testModelConnection(modelId);
      if (result.ok) {
        setVerifyByModel((prev) => ({ ...prev, [modelId]: 'ok' }));
        setVerifyMessage(result.message);
      } else {
        setVerifyByModel((prev) => ({ ...prev, [modelId]: 'failed' }));
        setVerifyMessage(result.message);
      }
    } catch (err) {
      setVerifyByModel((prev) => ({ ...prev, [modelId]: 'failed' }));
      setVerifyMessage(err instanceof Error ? err.message : 'Connection test failed.');
    }
  };

  const activeVerify = activeModelId ? verifyByModel[activeModelId] ?? 'idle' : 'idle';

  const footerStatus = (() => {
    if (configuredModels.length === 0 || !activeAvailable) return 'No usable model';
    if (activeVerify === 'testing') return 'Testing connection…';
    if (activeVerify === 'ok') return 'Connection verified';
    if (activeVerify === 'failed') return 'Connection failed';
    return 'Key detected (not verified)';
  })();

  return (
    <div className="flex-1 flex flex-col h-full bg-surface-bright text-on-surface select-none leading-normal">
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-on-surface">layers</span>
            <h2 className="text-base font-bold text-on-surface tracking-tight font-sans">AI Workspace Models</h2>
          </div>
          <p className="text-xs text-on-surface-variant font-sans leading-relaxed">
            Models appear only when a credential is detected. Use Test connection to confirm the provider accepts API calls.
          </p>
        </div>

        {error && (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2">{error}</p>
        )}

        {verifyMessage && (
          <p
            className={`text-xs rounded-lg px-3 py-2 border ${
              activeVerify === 'ok'
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

        {showConnectForm ? (
          <form onSubmit={(e) => void handleConnectProvider(e)} className="p-4 bg-surface-container border border-outline rounded-xl space-y-4 text-left">
            <h3 className="text-xs font-bold text-on-surface">Connect Provider API Key</h3>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">Provider</label>
              <select
                value={providerId}
                onChange={(e) => setProviderId(e.target.value)}
                className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface"
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
              <input
                type="password"
                required
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-••••••••"
                className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowConnectForm(false)} className="px-3 py-1.5 text-xs font-bold border border-outline rounded-lg">
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
              <p className="text-[10.5px] text-on-surface-variant">Add an API key to enable built-in models for that provider.</p>
            </div>
            <button type="button" onClick={() => setShowConnectForm(true)} className="bg-primary text-on-primary px-3.5 py-1.5 rounded-lg text-xs font-bold">
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
                        {isActive && (
                          <span className="text-[8.5px] uppercase font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.2 rounded font-extrabold">
                            Active
                          </span>
                        )}
                        {verify === 'ok' && (
                          <span className="text-[8.5px] uppercase font-mono bg-emerald-50 text-emerald-800 border border-emerald-200 px-1.5 py-0.2 rounded font-extrabold">
                            Verified
                          </span>
                        )}
                        {verify === 'failed' && (
                          <span className="text-[8.5px] uppercase font-mono bg-rose-50 text-rose-800 border border-rose-200 px-1.5 py-0.2 rounded font-extrabold">
                            Test failed
                          </span>
                        )}
                      </div>
                      <p className="text-[11.5px] text-on-surface-variant">{model.description}</p>
                    </div>
                    <div className="flex items-center gap-2 justify-end flex-shrink-0 flex-wrap">
                      <button
                        type="button"
                        disabled={loading || verify === 'testing'}
                        onClick={() => void handleTestConnection(model.id)}
                        className="bg-surface-container hover:bg-surface-container-high border border-outline text-on-surface px-3 py-1.5 rounded-lg text-[10.5px] font-bold disabled:opacity-50"
                      >
                        {verify === 'testing' ? 'Testing…' : 'Test connection'}
                      </button>
                      {isActive ? (
                        <span className="material-symbols-outlined text-[20px] text-on-primary bg-primary p-1.5 rounded-full border border-outline/50">
                          check
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled={loading}
                          onClick={() => void handleActivate(model.id)}
                          className="bg-surface-container hover:bg-primary hover:text-on-primary border border-outline text-on-surface px-3 py-1.5 rounded-lg text-[10.5px] font-bold disabled:opacity-50"
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
              Test active model
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
