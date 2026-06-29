import React, { useCallback, useEffect, useState } from 'react';
import {
  addCustomImageModel,
  deleteCustomModel,
  deleteProviderCredential,
  fetchModelsConfig,
  loadModelVerifyState,
  mapModelConfigToUi,
  pruneModelVerifyCache,
  PROVIDER_LABELS,
  removeModelVerifyResults,
  rehydrateCcSwitchModels,
  saveModelVerifyResult,
  saveModelsConfig,
  testModelConnection,
  type ProviderEntry,
} from '../services/modelsApi';
import { BTN_GHOST, BTN_PRIMARY, BTN_SECONDARY, BTN_ICON } from './ui/buttonStyles';
import { BADGE_NEUTRAL, BADGE_PRIMARY, BADGE_SUCCESS, CARD_SUBTLE } from './ui/surfaceStyles';
import { LegacyIcon } from './ui/LegacyIcon';

interface ModelItem {
  id: string;
  name: string;
  provider: string;
  providerId: string;
  modelKind?: 'chat' | 'image';
  imageBackend?: string;
  available: boolean;
  contextWindow: string;
  temperature: number;
  sourceSummary: string;
  credentialSourceLabel: string | null;
  endpoint: string | null;
  clutchManaged: boolean;
  isCcSwitch: boolean;
  isCustom?: boolean;
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
const IMAGE_BACKENDS = [
  { id: '', label: 'Auto-detect from URL' },
  { id: 'agnes', label: 'Agnes Image API' },
  { id: 'openai_images', label: 'OpenAI-compatible /v1/images/generations' },
] as const;

function verifyStatusLabel(verify: VerifyState): string | null {
  if (verify === 'testing') return 'Testing…';
  if (verify === 'ok') return 'Ready';
  if (verify === 'failed') return 'Connection failed';
  return null;
}

export const ModelsManager: React.FC<ModelsManagerProps> = ({
  activeModelId,
  setActiveModelId,
  selectedModel,
  setSelectedModel,
  configuredModels,
  setConfiguredModels,
}) => {
  const [showConnectForm, setShowConnectForm] = useState(false);
  const [showAddImageForm, setShowAddImageForm] = useState(false);
  const [imageName, setImageName] = useState('');
  const [imageApiModel, setImageApiModel] = useState('');
  const [imageBaseUrl, setImageBaseUrl] = useState('https://apihub.agnes-ai.com');
  const [imageProviderId, setImageProviderId] = useState('custom');
  const [imageBackend, setImageBackend] = useState('');
  const [imageApiKey, setImageApiKey] = useState('');
  const [savingImageModel, setSavingImageModel] = useState(false);
  const [deletingModelId, setDeletingModelId] = useState<string | null>(null);
  const [pendingRemove, setPendingRemove] = useState<{ id: string; name: string } | null>(null);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const [providerId, setProviderId] = useState<string>('deepseek');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activatingModelId, setActivatingModelId] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState(false);
  const [deletingProviderId, setDeletingProviderId] = useState<string | null>(null);
  const [syncingCcSwitch, setSyncingCcSwitch] = useState(false);
  const [ccSwitchSyncMessage, setCcSwitchSyncMessage] = useState<{
    tone: 'success' | 'error';
    text: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeAvailable, setActiveAvailable] = useState(true);
  const [providers, setProviders] = useState<Record<string, ProviderEntry>>({});
  const initialVerify = loadModelVerifyState();
  const [verifyByModel, setVerifyByModel] = useState<Record<string, VerifyState>>(() => ({
    ...initialVerify.verifyByModel,
  }));
  const [verifyMessageByModel, setVerifyMessageByModel] = useState<Record<string, string>>(
    () => ({ ...initialVerify.verifyMessageByModel }),
  );

  const applyConfig = useCallback(
    (config: Awaited<ReturnType<typeof fetchModelsConfig>>) => {
      const mapped = mapModelConfigToUi(config);
      setConfiguredModels(mapped.models);
      setProviders(mapped.providers);
      setActiveModelId(mapped.activeModelId);
      setActiveAvailable(mapped.activeAvailable);
      const active = mapped.models.find((m) => m.id === mapped.activeModelId);
      setSelectedModel(active?.name ?? '');
      pruneModelVerifyCache(mapped.models.map((model) => model.id));
      return mapped.models;
    },
    [setActiveModelId, setConfiguredModels, setSelectedModel],
  );

  const refresh = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setLoading(true);
    setError(null);
    try {
      const config = await fetchModelsConfig();
      return applyConfig(config);
    } catch {
      setConfiguredModels([]);
      setProviders({});
      setError('Cannot reach Clutch sidecar — start the backend on port 8124 (dev) or reopen the packaged app.');
      return [];
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, [applyConfig, setConfiguredModels]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleTestConnection = useCallback(async (modelId: string) => {
    setVerifyByModel((prev) => ({ ...prev, [modelId]: 'testing' }));
    setError(null);
    try {
      const result = await testModelConnection(modelId);
      const nextState: VerifyState = result.ok ? 'ok' : 'failed';
      setVerifyByModel((prev) => ({ ...prev, [modelId]: nextState }));
      setVerifyMessageByModel((prev) => ({ ...prev, [modelId]: result.message }));
      saveModelVerifyResult(modelId, result.ok, result.message);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Connection test failed.';
      setVerifyByModel((prev) => ({ ...prev, [modelId]: 'failed' }));
      setVerifyMessageByModel((prev) => ({ ...prev, [modelId]: message }));
      saveModelVerifyResult(modelId, false, message);
    }
  }, []);

  const openConnectForm = (provider?: string) => {
    setEditingProviderId(provider ?? null);
    setProviderId(provider ?? 'deepseek');
    setApiKey('');
    setShowApiKey(false);
    setShowConnectForm(true);
    setError(null);
  };

  const closeConnectForm = () => {
    setShowConnectForm(false);
    setShowApiKey(false);
    setEditingProviderId(null);
  };

  const closeAddImageForm = () => {
    setShowAddImageForm(false);
    setImageName('');
    setImageApiModel('');
    setImageBaseUrl('https://apihub.agnes-ai.com');
    setImageProviderId('custom');
    setImageBackend('');
    setImageApiKey('');
  };

  const handleAddImageModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!imageName.trim() || !imageApiModel.trim() || !imageBaseUrl.trim()) return;
    setSavingImageModel(true);
    setError(null);
    try {
      const result = await addCustomImageModel({
        name: imageName.trim(),
        api_model: imageApiModel.trim(),
        base_url: imageBaseUrl.trim(),
        provider_id: imageProviderId,
        image_backend: imageBackend as '' | 'agnes' | 'openai_images',
        api_key: imageApiKey.trim() || undefined,
      });
      closeAddImageForm();
      const models = await refresh({ silent: true });
      const created = models.find((m) => m.id === result.model_id);
      if (created?.available) {
        void handleTestConnection(result.model_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add image model.');
    } finally {
      setSavingImageModel(false);
    }
  };

  const handleRemoveModel = async () => {
    if (!pendingRemove) return;
    const { id: modelId, name: modelName } = pendingRemove;
    setPendingRemove(null);
    setDeletingModelId(modelId);
    setError(null);
    try {
      const config = await deleteCustomModel(modelId);
      removeModelVerifyResults([modelId]);
      applyConfig(config);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not remove "${modelName}".`);
    } finally {
      setDeletingModelId(null);
    }
  };

  const handleActivate = async (modelId: string) => {
    setActivatingModelId(modelId);
    setError(null);
    try {
      await saveModelsConfig({ active_model_id: modelId });
      await refresh({ silent: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not switch to this model.');
    } finally {
      setActivatingModelId(null);
    }
  };

  const handleConnectProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    const savedProviderId = providerId;
    setSavingKey(true);
    setError(null);
    try {
      await saveModelsConfig({ provider_id: savedProviderId, api_key: apiKey.trim() });
      closeConnectForm();
      const models = await refresh({ silent: true });
      const providerModels = models.filter((model) => model.providerId === savedProviderId);
      void Promise.all(providerModels.map((model) => handleTestConnection(model.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save API key.');
    } finally {
      setSavingKey(false);
    }
  };

  const handleDeleteProvider = async (targetProviderId: string) => {
    const message = `Remove the saved API key for ${PROVIDER_LABELS[targetProviderId] ?? targetProviderId}?`;
    if (!window.confirm(message)) return;

    const removedModelIds = new Set(
      configuredModels.filter((model) => model.providerId === targetProviderId).map((model) => model.id),
    );
    setDeletingProviderId(targetProviderId);
    setError(null);
    try {
      await deleteProviderCredential(targetProviderId);
      removeModelVerifyResults(removedModelIds);
      setVerifyByModel((prev) =>
        Object.fromEntries(Object.entries(prev).filter(([modelId]) => !removedModelIds.has(modelId))),
      );
      setVerifyMessageByModel((prev) =>
        Object.fromEntries(Object.entries(prev).filter(([modelId]) => !removedModelIds.has(modelId))),
      );
      closeConnectForm();
      await refresh({ silent: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove saved key.');
      await refresh({ silent: true });
    } finally {
      setDeletingProviderId(null);
    }
  };

  const handleRehydrateCcSwitch = async () => {
    setSyncingCcSwitch(true);
    setCcSwitchSyncMessage(null);
    setError(null);
    try {
      const result = await rehydrateCcSwitchModels();
      await refresh({ silent: true });
      setCcSwitchSyncMessage({
        tone: result.ok ? 'success' : 'error',
        text: result.message,
      });
    } catch (err) {
      setCcSwitchSyncMessage({
        tone: 'error',
        text: err instanceof Error ? err.message : 'CC Switch import failed.',
      });
    } finally {
      setSyncingCcSwitch(false);
    }
  };

  const activeVerify = activeModelId ? verifyByModel[activeModelId] ?? 'idle' : 'idle';
  const activeVerifyMessage = activeModelId ? verifyMessageByModel[activeModelId] : undefined;
  const editingProvider = editingProviderId ? providers[editingProviderId] : undefined;

  const currentStatusLine = (() => {
    if (!activeModelId || !activeAvailable) {
      return 'Pick a model below or add an API key to get started.';
    }
    if (activeVerify === 'testing') return 'Testing connection…';
    if (activeVerify === 'ok') return activeVerifyMessage ?? 'Ready to use.';
    if (activeVerify === 'failed') return activeVerifyMessage ?? 'Last test failed — fix the key or choose another model.';
    return 'Not tested yet — press Test when you want to verify.';
  })();

  const statusTone =
    !activeAvailable || activeVerify === 'failed'
      ? 'rose'
      : activeVerify === 'ok'
        ? 'emerald'
        : 'neutral';

  return (
    <div className="flex-1 flex flex-col h-full bg-surface-bright text-on-surface select-none leading-normal">
      <div className="flex-1 overflow-y-auto px-6 pb-6 pt-14 pr-12 space-y-5">
        <div className="flex items-start justify-between gap-4">
          <header className="text-left space-y-1 min-w-0">
            <h2 className="text-base font-bold text-on-surface tracking-tight font-sans">AI Workspace Models</h2>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              Choose which model Clutch uses for chat and workflows.
            </p>
          </header>
          <div className="flex flex-shrink-0 gap-2">
            <button
              type="button"
              onClick={() => {
                closeConnectForm();
                setShowAddImageForm((v) => !v);
              }}
              className={`${BTN_SECONDARY} text-[10.5px] whitespace-nowrap`}
            >
              Add image model
            </button>
            <button
              type="button"
              onClick={() => {
                closeAddImageForm();
                openConnectForm();
              }}
              className={`${BTN_PRIMARY} text-[10.5px] whitespace-nowrap`}
            >
              Add API key
            </button>
          </div>
        </div>

        {showAddImageForm && (
          <form
            onSubmit={(e) => void handleAddImageModel(e)}
            className={`${CARD_SUBTLE} space-y-4 text-left`}
          >
            <div>
              <h3 className="text-xs font-bold text-on-surface">Add custom image model</h3>
              <p className="text-[11px] text-on-surface-variant mt-0.5">
                Register a text-to-image endpoint without editing code. Use Agnes or any OpenAI-compatible gateway.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                  Display name
                </label>
                <input
                  required
                  value={imageName}
                  onChange={(e) => setImageName(e.target.value)}
                  placeholder="My Image Model"
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                  API model id
                </label>
                <input
                  required
                  value={imageApiModel}
                  onChange={(e) => setImageApiModel(e.target.value)}
                  placeholder="agnes-image-2.1-flash"
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono text-on-surface"
                />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                  Base URL
                </label>
                <input
                  required
                  value={imageBaseUrl}
                  onChange={(e) => setImageBaseUrl(e.target.value)}
                  placeholder="https://apihub.agnes-ai.com"
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono text-on-surface"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                  API key provider
                </label>
                <select
                  value={imageProviderId}
                  onChange={(e) => setImageProviderId(e.target.value)}
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
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                  Image backend
                </label>
                <select
                  value={imageBackend}
                  onChange={(e) => setImageBackend(e.target.value)}
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface"
                >
                  {IMAGE_BACKENDS.map((item) => (
                    <option key={item.id || 'auto'} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1 sm:col-span-2">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                  API key (optional)
                </label>
                <input
                  type="password"
                  value={imageApiKey}
                  onChange={(e) => setImageApiKey(e.target.value)}
                  placeholder="Save key for the selected provider"
                  className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono text-on-surface"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={closeAddImageForm} className={`${BTN_GHOST} text-[10.5px]`}>
                Cancel
              </button>
              <button
                type="submit"
                disabled={savingImageModel}
                className={`${BTN_PRIMARY} text-[10.5px] disabled:opacity-50`}
              >
                {savingImageModel ? 'Saving…' : 'Save image model'}
              </button>
            </div>
          </form>
        )}

        {showConnectForm && (
          <form
            onSubmit={(e) => void handleConnectProvider(e)}
            className="p-4 bg-surface-container border border-outline rounded-xl space-y-4 text-left"
          >
            <div>
              <h3 className="text-xs font-bold text-on-surface">
                {editingProviderId ? 'Update API key' : 'Add API key'}
              </h3>
              <p className="text-[11px] text-on-surface-variant mt-0.5">
                Saved in Clutch and used for built-in models of this provider.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                  Provider
                </label>
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
                <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                  API key
                </label>
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
                    className={`${BTN_GHOST} absolute right-3 p-0 border-0 text-on-surface-variant hover:text-on-surface hover:bg-transparent`}
                  >
                    <LegacyIcon name={showApiKey ? 'visibility' : 'visibility_off'} className="text-[18px]" />
                  </button>
                </div>
              </div>
            </div>
            <div className="flex justify-between gap-2 flex-wrap">
              <div>
                {editingProvider?.clutch_managed && (
                  <button
                    type="button"
                    disabled={deletingProviderId === providerId}
                    onClick={() => void handleDeleteProvider(providerId)}
                    className={`${BTN_GHOST} text-[10.5px] border-rose-200 text-rose-700 hover:bg-rose-50 disabled:opacity-50`}
                  >
                    {deletingProviderId === providerId ? 'Removing…' : 'Remove saved key'}
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={closeConnectForm}
                  className={`${BTN_GHOST} text-[10.5px]`}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingKey}
                  className={`${BTN_PRIMARY} text-[10.5px] disabled:opacity-50`}
                >
                  {savingKey ? 'Saving…' : 'Save'}
                </button>
              </div>
            </div>
          </form>
        )}

        {pendingRemove && (
          <div className="p-4 bg-rose-50/70 border border-rose-200 rounded-xl space-y-3 text-left">
            <p className="text-xs text-rose-900">
              Remove <span className="font-bold">{pendingRemove.name}</span> from your model list?
              {pendingRemove.id.startsWith('custom-')
                ? ' This custom model will be deleted permanently.'
                : pendingRemove.id.startsWith('cc-switch-')
                  ? ' CC Switch imported models are hidden from the list and can be restored by clicking Import models.'
                  : ' Built-in models are hidden from the list and can be restored by editing models.json.'}
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPendingRemove(null)}
                className={`${BTN_GHOST} text-[10.5px]`}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleRemoveModel()}
                className={`${BTN_PRIMARY} text-[10.5px] bg-rose-700 border-rose-700 hover:bg-rose-800 hover:border-rose-800`}
              >
                Remove
              </button>
            </div>
          </div>
        )}

        {error && (
          <p className="text-xs text-rose-800 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2 text-left">
            {error}
          </p>
        )}

        <section
          className={`rounded-xl border p-4 text-left ${
            statusTone === 'rose'
              ? 'bg-rose-50/60 border-rose-200'
              : statusTone === 'emerald'
                ? 'bg-emerald-50/50 border-emerald-200'
                : 'bg-surface-container border-outline'
          }`}
        >
          <p className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">Current model</p>
          <p className="text-sm font-bold text-on-surface mt-1">{selectedModel || 'None selected'}</p>
          <p
            className={`text-xs mt-1 leading-relaxed ${
              statusTone === 'rose'
                ? 'text-rose-800'
                : statusTone === 'emerald'
                  ? 'text-emerald-800'
                  : 'text-on-surface-variant'
            }`}
          >
            {currentStatusLine}
          </p>
        </section>

        <section className="space-y-3 text-left">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-on-surface">Available models</h3>
            <span className="text-[10px] text-on-surface-variant">{configuredModels.length} listed</span>
          </div>

          {loading && configuredModels.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-6 text-center">Loading models…</p>
          ) : configuredModels.length === 0 ? (
            <div className="rounded-xl border border-dashed border-outline/70 p-6 text-center space-y-3">
              <p className="text-xs text-on-surface-variant">No models yet — add an API key or import from CC Switch.</p>
              <button
                type="button"
                onClick={() => openConnectForm()}
                className={`${BTN_PRIMARY} text-xs`}
              >
                Add API key
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2">
              {configuredModels.map((model) => {
                const isActive = activeModelId === model.id;
                const verify = verifyByModel[model.id] ?? 'idle';
                const statusLabel = verifyStatusLabel(verify);
                const rowMessage = verifyMessageByModel[model.id];
                const canUse = model.available;
                const canRemove = !isActive;
                return (
                  <div
                    key={model.id}
                    onClick={() => {
                      if (canUse && !isActive && !activatingModelId) {
                        void handleActivate(model.id);
                      }
                    }}
                    className={`group p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all ${
                      isActive
                        ? 'bg-surface-container border-primary shadow-xs'
                        : `bg-surface border-outline/65 ${
                            canUse && !activatingModelId
                              ? 'cursor-pointer hover:border-primary/50 hover:shadow-xs'
                              : ''
                          }`
                    } ${!canUse ? 'opacity-80' : ''}`}
                  >
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold text-on-surface">{model.name}</span>
                        <span className="text-[10px] text-on-surface-variant">{model.provider}</span>
                        {model.modelKind === 'image' && (
                          <span className={BADGE_PRIMARY}>Image</span>
                        )}
                        {model.isCustom && (
                          <span className={BADGE_NEUTRAL}>Custom</span>
                        )}
                        {!canUse && (
                          <span className={BADGE_NEUTRAL}>Needs key</span>
                        )}
                        {isActive && (
                          <span className={BADGE_PRIMARY}>In use</span>
                        )}
                        {statusLabel && (
                          <span
                            className={
                              verify === 'ok'
                                ? BADGE_SUCCESS
                                : verify === 'failed'
                                  ? BADGE_NEUTRAL
                                  : BADGE_NEUTRAL
                            }
                          >
                            {statusLabel}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-on-surface-variant">{model.sourceSummary}</p>
                      {model.endpoint && (
                        <p className="text-[10px] text-on-surface-variant/80 font-mono truncate">{model.endpoint}</p>
                      )}
                      {verify === 'failed' && rowMessage && (
                        <p className="text-[10.5px] text-rose-800">{rowMessage}</p>
                      )}
                      {model.clutchManaged && !showConnectForm && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            openConnectForm(model.providerId);
                          }}
                          className="text-[10px] font-bold text-primary hover:underline"
                        >
                          Change {model.provider} key
                        </button>
                      )}
                    </div>
                    <div
                      className={`flex items-center gap-1 flex-shrink-0 ml-2 transition-opacity ${
                        verify === 'testing' || deletingModelId === model.id
                          ? 'opacity-100'
                          : 'opacity-0 group-hover:opacity-100'
                      }`}
                    >
                      <button
                        type="button"
                        disabled={!canUse || verify === 'testing'}
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleTestConnection(model.id);
                        }}
                        className={BTN_ICON}
                        title={verify === 'testing' ? 'Testing connection' : verify === 'idle' ? 'Test connection' : 'Retest connection'}
                        aria-label={verify === 'testing' ? 'Testing connection' : verify === 'idle' ? 'Test connection' : 'Retest connection'}
                      >
                        <LegacyIcon
                          name={verify === 'testing' ? 'progress_activity' : 'sync'}
                          className="text-[16px]"
                          spin={verify === 'testing'}
                        />
                      </button>
                      {canRemove && (
                        <button
                          type="button"
                          disabled={deletingModelId === model.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            setPendingRemove({ id: model.id, name: model.name });
                          }}
                          className={`${BTN_ICON} hover:bg-rose-50 text-red-500 hover:text-red-700 disabled:opacity-50`}
                          title="Remove model"
                          aria-label="Remove model"
                        >
                          <LegacyIcon name="delete" className="text-[16px]" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="pt-2 text-center space-y-2">
            <p className="text-[11px] text-on-surface-variant">
              Already use CC Switch?{' '}
              <button
                type="button"
                disabled={syncingCcSwitch}
                onClick={() => void handleRehydrateCcSwitch()}
                className="font-bold text-primary hover:underline disabled:opacity-50"
              >
                {syncingCcSwitch ? 'Importing…' : 'Import models'}
              </button>
            </p>
            {ccSwitchSyncMessage && (
              <p
                className={`text-[11px] rounded-lg px-3 py-2 border inline-block ${
                  ccSwitchSyncMessage.tone === 'success'
                    ? 'text-emerald-700 bg-emerald-50 border-emerald-100'
                    : 'text-rose-700 bg-rose-50 border-rose-100'
                }`}
              >
                {ccSwitchSyncMessage.text}
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};
