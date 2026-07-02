import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  addCustomChatModel,
  addCustomImageModel,
  addCustomVideoModel,
  deleteCustomModel,
  fetchOpencodeZenModels,
  fetchProviderApiKey,
  fetchModelsConfig,
  loadModelVerifyState,
  mapModelConfigToUi,
  ModelsConfigError,
  pruneModelVerifyCache,
  PROVIDER_LABELS,
  removeModelVerifyResults,
  rehydrateCcSwitchModels,
  saveModelVerifyResult,
  saveModelsConfig,
  testModelConnection,
  updateCustomModel,
  type ProviderEntry,
} from '../services/modelsApi';
import { BTN_GHOST, BTN_PRIMARY, BTN_ICON } from './ui/buttonStyles';
import { SettingsPageHeader, SettingsPageShell } from './ui/SettingsPageHeader';
import { BADGE_NEUTRAL, BADGE_PRIMARY, BADGE_SUCCESS } from './ui/surfaceStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import {
  AGNES_BUILTIN_MODEL_ID,
  AGNES_DEFAULTS,
  BUILTIN_PROVIDER_IDS,
  DEFAULT_CHAT_MODEL_BY_PROVIDER,
  defaultProviderForModelKind,
  inferImageBackend,
  OPENCODE_BUILTIN_MODELS,
  providersForModelKind,
  type ModelKind,
} from '../services/modelProviderPresets';
import { AgentCapabilityTabs } from './AgentCapabilityTabs';
import { ClaudeCodeModelsPanel } from './ClaudeCodeModelsPanel';
import { OpenCodeModelsPanel } from './OpenCodeModelsPanel';
import { MoreAgentsComingSoon } from './MoreAgentsComingSoon';
import type { AgentCapabilityTabId } from '../services/agentCapabilityTiers';
import { consumeSettingsAgentTab } from '../services/cliConfigApi';

interface ModelItem {
  id: string;
  name: string;
  provider: string;
  providerId: string;
  modelKind?: 'chat' | 'image' | 'video';
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
type ModelsModal =
  | { type: 'add'; modelKind: ModelKind }
  | { type: 'edit-key'; providerId: string }
  | { type: 'edit-custom'; modelId: string; modelKind: ModelKind; baseUrl: string; apiModel: string };

interface ModelsManagerProps {
  activeModelId: string;
  setActiveModelId: (id: string) => void;
  selectedModel: string;
  setSelectedModel: (name: string) => void;
  configuredModels: ModelItem[];
  setConfiguredModels: React.Dispatch<React.SetStateAction<ModelItem[]>>;
}

import { useLanguage } from './LanguageContext';

const CONNECTABLE_PROVIDERS = [...BUILTIN_PROVIDER_IDS, 'custom'] as const;

function defaultOpencodeModelSelection(): string {
  return DEFAULT_CHAT_MODEL_BY_PROVIDER.opencode;
}

export const ModelsManager: React.FC<ModelsManagerProps> = ({
  activeModelId,
  setActiveModelId,
  selectedModel,
  setSelectedModel,
  configuredModels,
  setConfiguredModels,
}) => {
  const { t } = useLanguage();

  const verifyStatusLabel = (verify: VerifyState): string | null => {
    if (verify === 'testing') return t('Testing…');
    if (verify === 'ok') return t('Ready');
    if (verify === 'failed') return t('Connection failed');
    return null;
  };

  const [activeModal, setActiveModal] = useState<ModelsModal | null>(null);
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const addMenuRef = useRef<HTMLDivElement>(null);
  const [addModelProviderId, setAddModelProviderId] = useState<string>('agnes');
  const [addModelApiKey, setAddModelApiKey] = useState('');
  const [addModelCustomBaseUrl, setAddModelCustomBaseUrl] = useState('');
  const [addModelCustomApiModel, setAddModelCustomApiModel] = useState('');
  const [opencodeModels, setOpencodeModels] = useState<
    Array<{ id: string; api_model: string; name: string; supported: boolean }>
  >(() => [...OPENCODE_BUILTIN_MODELS]);
  const [loadingOpencodeModels, setLoadingOpencodeModels] = useState(false);
  const [opencodeListMessage, setOpencodeListMessage] = useState<string | null>(null);
  const [selectedOpencodeModelId, setSelectedOpencodeModelId] = useState(() =>
    defaultOpencodeModelSelection(),
  );
  const [editCustomBaseUrl, setEditCustomBaseUrl] = useState('');
  const [editCustomApiModel, setEditCustomApiModel] = useState('');
  const [editCustomApiKey, setEditCustomApiKey] = useState('');
  const [savingAddModel, setSavingAddModel] = useState(false);
  const [savingEditModel, setSavingEditModel] = useState(false);
  const [deletingModelId, setDeletingModelId] = useState<string | null>(null);
  const [providerId, setProviderId] = useState<string>('deepseek');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rescanning, setRescanning] = useState(false);
  const [activatingModelId, setActivatingModelId] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState(false);
  const [loadingKey, setLoadingKey] = useState(false);
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
  const [capabilityTab, setCapabilityTab] = useState<AgentCapabilityTabId>('clutch');

  useEffect(() => {
    const stashed = consumeSettingsAgentTab();
    if (stashed) setCapabilityTab(stashed);
  }, []);

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
    } catch (err) {
      setConfiguredModels([]);
      setProviders({});
      if (err instanceof ModelsConfigError) {
        if (err.kind === 'unauthorized') {
          setError(t('Sidecar session expired — quit Clutch (Cmd+Q) and reopen the app.'));
        } else if (err.kind === 'server') {
          setError(t('Sidecar backend error — quit Clutch (Cmd+Q) and reopen the app.'));
        } else {
          setError(t('Cannot reach Clutch sidecar — start the backend on port 8124 (dev) or reopen the packaged app.'));
        }
      } else {
        setError(t('Cannot reach Clutch sidecar — start the backend on port 8124 (dev) or reopen the packaged app.'));
      }
      return [];
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, [applyConfig, setConfiguredModels]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const resync = () => {
      void refresh({ silent: true });
    };
    const onVisibility = () => {
      if (document.visibilityState === 'visible') resync();
    };
    window.addEventListener('focus', resync);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('focus', resync);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [refresh]);

  const handleRescan = useCallback(async () => {
    setRescanning(true);
    try {
      await refresh({ silent: true });
    } finally {
      setRescanning(false);
    }
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
      const message = err instanceof Error ? err.message : t('Connection test failed.');
      setVerifyByModel((prev) => ({ ...prev, [modelId]: 'failed' }));
      setVerifyMessageByModel((prev) => ({ ...prev, [modelId]: message }));
      saveModelVerifyResult(modelId, false, message);
    }
  }, []);

  useEffect(() => {
    if (!addMenuOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      if (addMenuRef.current && !addMenuRef.current.contains(event.target as Node)) {
        setAddMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [addMenuOpen]);

  const resetAddModelForm = (kind?: ModelKind) => {
    setAddModelProviderId(kind ? defaultProviderForModelKind(kind) : 'deepseek');
    setAddModelApiKey('');
    setAddModelCustomBaseUrl('');
    setAddModelCustomApiModel('');
    applyOpencodeProviderDefaults();
  };

  const resetOpencodeForm = () => {
    setOpencodeModels([...OPENCODE_BUILTIN_MODELS]);
    setLoadingOpencodeModels(false);
    setOpencodeListMessage(null);
    setSelectedOpencodeModelId(defaultOpencodeModelSelection());
  };

  const applyOpencodeProviderDefaults = () => {
    setOpencodeModels([...OPENCODE_BUILTIN_MODELS]);
    setOpencodeListMessage(null);
    setSelectedOpencodeModelId(defaultOpencodeModelSelection());
  };

  const resetEditCustomForm = () => {
    setEditCustomBaseUrl('');
    setEditCustomApiModel('');
    setEditCustomApiKey('');
  };

  const closeModal = () => {
    setActiveModal(null);
    resetAddModelForm();
    resetEditCustomForm();
    resetOpencodeForm();
    setApiKey('');
    setShowApiKey(false);
    setError(null);
  };

  const refreshOpencodeCatalog = useCallback(async () => {
    setLoadingOpencodeModels(true);
    setOpencodeListMessage(null);
    try {
      const result = await fetchOpencodeZenModels();
      if (!result.ok || result.models.length === 0) {
        setOpencodeListMessage(result.message ?? t('Could not refresh model list from opencode.ai.'));
        return;
      }
      setOpencodeModels(result.models);
      setSelectedOpencodeModelId((current) => {
        if (current && result.models.some((model) => model.id === current)) return current;
        const free = result.models.find((model) => model.api_model.endsWith('-free'));
        return free?.id ?? result.models[0]?.id ?? defaultOpencodeModelSelection();
      });
      setOpencodeListMessage(t('Model list updated from opencode.ai.'));
    } catch (err) {
      setOpencodeListMessage(
        err instanceof Error ? err.message : t('Could not refresh model list from opencode.ai.'),
      );
    } finally {
      setLoadingOpencodeModels(false);
    }
  }, [t]);

  const renderOpencodeModelPicker = () => (
    <div className="space-y-1 sm:col-span-2">
      <div className="flex items-center justify-between gap-2">
        <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
          {t('Model')}
        </label>
        <button
          type="button"
          onClick={() => void refreshOpencodeCatalog()}
          disabled={loadingOpencodeModels}
          className={`${BTN_GHOST} text-[10px] px-2 py-1 border border-outline/60`}
        >
          {loadingOpencodeModels ? t('Refreshing…') : t('Refresh models')}
        </button>
      </div>
      <select
        value={selectedOpencodeModelId}
        onChange={(e) => {
          setSelectedOpencodeModelId(e.target.value);
          setOpencodeListMessage(null);
        }}
        className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface"
      >
        {opencodeModels.map((model) => (
          <option key={model.id} value={model.id}>
            {model.name}
          </option>
        ))}
      </select>
      {opencodeListMessage && (
        <p
          className={`text-[11px] ${
            opencodeListMessage.toLowerCase().includes('rejected') ||
            opencodeListMessage.toLowerCase().includes('no longer')
              ? 'text-rose-700'
              : 'text-on-surface-variant'
          }`}
        >
          {opencodeListMessage}
        </p>
      )}
    </div>
  );

  const openAddModal = (kind: ModelKind) => {
    setAddMenuOpen(false);
    setActiveModal({ type: 'add', modelKind: kind });
    setError(null);
    resetAddModelForm(kind);
    resetEditCustomForm();
    setApiKey('');
    setShowApiKey(false);
  };

  const openEditKeyModal = (provider?: string) => {
    const nextProviderId = provider ?? 'deepseek';
    setActiveModal({ type: 'edit-key', providerId: nextProviderId });
    setProviderId(nextProviderId);
    setApiKey('');
    resetOpencodeForm();
    setShowApiKey(false);
    setError(null);
    void (async () => {
      setLoadingKey(true);
      try {
        const key = await fetchProviderApiKey(nextProviderId);
        if (key) {
          setApiKey(key);
          if (nextProviderId === 'opencode' && activeModelId.startsWith('opencode-')) {
            setSelectedOpencodeModelId(activeModelId);
          }
        }
      } catch {
        // No saved key yet — user can enter a new one.
      } finally {
        setLoadingKey(false);
      }
    })();
  };

  const openEditCustomModal = (model: ModelItem) => {
    setActiveModal({
      type: 'edit-custom',
      modelId: model.id,
      modelKind: model.modelKind ?? 'chat',
      baseUrl: model.endpoint ?? '',
      apiModel: model.name,
    });
    setEditCustomBaseUrl(model.endpoint ?? '');
    setEditCustomApiModel(model.name);
    setEditCustomApiKey('');
    setError(null);
  };

  const addModelKind: ModelKind | null =
    activeModal?.type === 'add' ? activeModal.modelKind : null;

  const editingProviderId =
    activeModal?.type === 'edit-key' ? activeModal.providerId : null;

  const handleAddModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addModelKind || !addModelApiKey.trim()) return;
    setSavingAddModel(true);
    setError(null);
    try {
      const isBuiltinProvider = addModelProviderId !== 'custom';

      if (addModelKind === 'chat' && addModelProviderId === 'opencode') {
        if (!selectedOpencodeModelId) {
          setError(t('Select an OpenCode Zen model.'));
          return;
        }
        await saveModelsConfig({
          provider_id: 'opencode',
          api_key: addModelApiKey.trim(),
          active_model_id: selectedOpencodeModelId,
        });
        closeModal();
        const models = await refresh({ silent: true });
        const created = models.find((m) => m.id === selectedOpencodeModelId);
        if (created?.available) void handleTestConnection(selectedOpencodeModelId);
        return;
      }

      if (addModelKind === 'chat' && isBuiltinProvider) {
        const builtinId = DEFAULT_CHAT_MODEL_BY_PROVIDER[addModelProviderId];
        await saveModelsConfig({
          provider_id: addModelProviderId,
          api_key: addModelApiKey.trim(),
          ...(builtinId ? { active_model_id: builtinId } : {}),
        });
        closeModal();
        const models = await refresh({ silent: true });
        if (builtinId) {
          const created = models.find((m) => m.id === builtinId);
          if (created?.available) void handleTestConnection(builtinId);
        } else {
          const providerModels = models.filter((m) => m.providerId === addModelProviderId);
          void Promise.all(providerModels.map((m) => handleTestConnection(m.id)));
        }
        return;
      }

      if (isBuiltinProvider && addModelProviderId === 'agnes') {
        const builtinId = AGNES_BUILTIN_MODEL_ID[addModelKind];
        await saveModelsConfig({
          provider_id: 'agnes',
          api_key: addModelApiKey.trim(),
          active_model_id: builtinId,
        });
        closeModal();
        const models = await refresh({ silent: true });
        const created = models.find((m) => m.id === builtinId);
        if (created?.available) void handleTestConnection(builtinId);
        return;
      }

      const baseUrl = addModelCustomBaseUrl.trim();
      const apiModel = addModelCustomApiModel.trim();
      if (!baseUrl || !apiModel) {
        setError(t('Base URL and model id are required for custom gateways.'));
        return;
      }

      if (addModelKind === 'chat') {
        const result = await addCustomChatModel({
          name: apiModel,
          api_model: apiModel,
          base_url: baseUrl,
          provider_id: 'custom',
          api_key: addModelApiKey.trim(),
        });
        closeModal();
        const models = await refresh({ silent: true });
        const created = models.find((m) => m.id === result.model_id);
        if (created?.available) void handleTestConnection(result.model_id);
      } else if (addModelKind === 'image') {
        const result = await addCustomImageModel({
          name: apiModel,
          api_model: apiModel,
          base_url: baseUrl,
          provider_id: 'custom',
          image_backend: inferImageBackend(baseUrl),
          api_key: addModelApiKey.trim(),
        });
        closeModal();
        const models = await refresh({ silent: true });
        const created = models.find((m) => m.id === result.model_id);
        if (created?.available) void handleTestConnection(result.model_id);
      } else {
        const result = await addCustomVideoModel({
          name: apiModel,
          api_model: apiModel,
          base_url: baseUrl,
          provider_id: 'custom',
          video_backend: baseUrl.includes('agnes-ai.com') ? 'agnes' : undefined,
          api_key: addModelApiKey.trim(),
        });
        closeModal();
        const models = await refresh({ silent: true });
        const created = models.find((m) => m.id === result.model_id);
        if (created?.available) void handleTestConnection(result.model_id);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : t('Could not save model.');
      setError(message);
      if (addModelProviderId === 'opencode') {
        setOpencodeListMessage(message);
      }
    } finally {
      setSavingAddModel(false);
    }
  };

  const handleEditCustomModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (activeModal?.type !== 'edit-custom') return;
    const baseUrl = editCustomBaseUrl.trim();
    const apiModel = editCustomApiModel.trim();
    if (!baseUrl || !apiModel) return;
    setSavingEditModel(true);
    setError(null);
    try {
      const config = await updateCustomModel(activeModal.modelId, {
        name: apiModel,
        api_model: apiModel,
        base_url: baseUrl,
        ...(editCustomApiKey.trim() ? { api_key: editCustomApiKey.trim() } : {}),
      });
      applyConfig(config);
      closeModal();
      void handleTestConnection(activeModal.modelId);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Could not save model.'));
    } finally {
      setSavingEditModel(false);
    }
  };

  const handleRemoveModel = async (modelId: string, modelName: string) => {
    let message = t('Remove {name} from your model list?').replace('{name}', modelName);
    if (modelId.startsWith('custom-')) {
      message += ` ${t('Remove custom model permanently')}`;
    } else if (modelId.startsWith('cc-switch-')) {
      message += ` ${t('Hide CC Switch imported models')}`;
    } else {
      message += ` ${t('Hide built-in model')}`;
    }
    if (!window.confirm(message)) return;
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
      setError(err instanceof Error ? err.message : t('Could not switch to this model.'));
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
      await saveModelsConfig({
        provider_id: savedProviderId,
        api_key: apiKey.trim(),
        ...(savedProviderId === 'opencode' && selectedOpencodeModelId
          ? { active_model_id: selectedOpencodeModelId }
          : {}),
      });
      closeModal();
      const models = await refresh({ silent: true });
      const providerModels = models.filter((model) => model.providerId === savedProviderId);
      void Promise.all(providerModels.map((model) => handleTestConnection(model.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Could not save API key.'));
    } finally {
      setSavingKey(false);
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
        text: err instanceof Error ? err.message : t('CC Switch import failed.'),
      });
    } finally {
      setSyncingCcSwitch(false);
    }
  };

  const activeVerify = activeModelId ? verifyByModel[activeModelId] ?? 'idle' : 'idle';
  const activeVerifyMessage = activeModelId ? verifyMessageByModel[activeModelId] : undefined;

  const currentStatusLine = (() => {
    if (!activeModelId || !activeAvailable) {
      return t('Pick a model below or add an API key to get started.');
    }
    if (activeVerify === 'testing') return t('Testing connection…');
    if (activeVerify === 'ok') return activeVerifyMessage ? t(activeVerifyMessage) : t('Ready to use.');
    if (activeVerify === 'failed') {
      return activeVerifyMessage ? t(activeVerifyMessage) : t('Last test failed — fix the key or choose another model.');
    }
    return t('Not tested yet — press Test when you want to verify.');
  })();

  const statusTone =
    !activeAvailable || activeVerify === 'failed'
      ? 'rose'
      : activeVerify === 'ok'
        ? 'emerald'
        : 'neutral';

  return (
    <>
    <SettingsPageShell wide>
      <SettingsPageHeader
        isModalStyle
        icon="layers"
        title={t('Models by Agent')}
        description={t('Clutch models power the built-in agent. CLI tabs show each tool native model configuration.')}
        actions={
          capabilityTab === 'clutch' ? (
            <div className="flex flex-shrink-0 gap-2">
              <button
                type="button"
                onClick={() => void handleRescan()}
                disabled={loading || rescanning}
                className={`${BTN_GHOST} text-[10.5px] whitespace-nowrap disabled:opacity-50 inline-flex items-center gap-1`}
              >
                <LegacyIcon
                  name="sync"
                  className={`text-[13px] ${rescanning ? 'animate-spin' : ''}`}
                />
                {t('Rescan')}
              </button>
              <div className="relative" ref={addMenuRef}>
                <button
                  type="button"
                  onClick={() => setAddMenuOpen((open) => !open)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-[10.5px] font-semibold text-white bg-neutral-900 hover:bg-black border border-neutral-900 rounded-lg shadow-sm transition-colors"
                  aria-haspopup="menu"
                  aria-expanded={addMenuOpen}
                >
                  <LegacyIcon name="add" className="text-[13px]" />
                  {t('Add model')}
                  <LegacyIcon name="keyboard_arrow_down" className="text-[13px]" />
                </button>
                {addMenuOpen ? (
                  <div className="absolute right-0 top-full mt-1 min-w-[168px] bg-surface-bright border border-outline-variant rounded-lg shadow-lg py-1 z-30">
                    <button
                      type="button"
                      onClick={() => openAddModal('chat')}
                      className="w-full text-left px-3 py-2 text-[11px] hover:bg-surface-container-low text-on-surface"
                    >
                      {t('Add text model')}
                    </button>
                    <button
                      type="button"
                      onClick={() => openAddModal('image')}
                      className="w-full text-left px-3 py-2 text-[11px] hover:bg-surface-container-low text-on-surface"
                    >
                      {t('Add image model')}
                    </button>
                    <button
                      type="button"
                      onClick={() => openAddModal('video')}
                      className="w-full text-left px-3 py-2 text-[11px] hover:bg-surface-container-low text-on-surface"
                    >
                      {t('Add video model')}
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          ) : null
        }
      />

        <AgentCapabilityTabs activeTab={capabilityTab} onTabChange={setCapabilityTab} className="pb-1" />

        {capabilityTab === 'claude-cli' ? <ClaudeCodeModelsPanel /> : null}
        {capabilityTab === 'opencode-cli' ? <OpenCodeModelsPanel /> : null}
        {capabilityTab === 'more' ? <MoreAgentsComingSoon /> : null}

        {capabilityTab === 'clutch' ? (
        <>
        {error && !activeModal && (
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
          <p className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">{t('Current model')}</p>
          <p className="text-sm font-bold text-on-surface mt-1">{selectedModel || t('None selected')}</p>
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
            <h3 className="text-xs font-bold text-on-surface">{t('Available models')}</h3>
            <span className="text-[10px] text-on-surface-variant">{configuredModels.length} {t('listed')}</span>
          </div>

          {loading && configuredModels.length === 0 ? (
            <p className="text-xs text-on-surface-variant italic py-6 text-center">{t('Loading models…')}</p>
          ) : configuredModels.length === 0 ? (
            <div className="rounded-xl border border-dashed border-outline/70 p-6 text-center space-y-3">
              <p className="text-xs text-on-surface-variant">{t('No models yet — add an API key or import from CC Switch.')}</p>
              <button
                type="button"
                onClick={() => openEditKeyModal()}
                className={`${BTN_PRIMARY} text-xs`}
              >
                {t('Add API key')}
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
                const canEdit = model.clutchManaged || model.isCustom;
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
                          <span className={BADGE_PRIMARY}>{t('Image')}</span>
                        )}
                        {model.modelKind === 'video' && (
                          <span className={BADGE_PRIMARY}>{t('Video')}</span>
                        )}
                        {model.isCustom && (
                          <span className={BADGE_NEUTRAL}>{t('Custom')}</span>
                        )}
                        {!canUse && (
                          <span className={BADGE_NEUTRAL}>{t('Needs key')}</span>
                        )}
                        {isActive && (
                          <span className={BADGE_PRIMARY}>{t('In use')}</span>
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
                        <p className="text-[10.5px] text-rose-800">{t(rowMessage)}</p>
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
                        title={
                          verify === 'testing'
                            ? t('Testing connection')
                            : verify === 'idle'
                              ? t('Test connection')
                              : t('Retest connection')
                        }
                        aria-label={
                          verify === 'testing'
                            ? t('Testing connection')
                            : verify === 'idle'
                              ? t('Test connection')
                              : t('Retest connection')
                        }
                      >
                        <LegacyIcon
                          name={verify === 'testing' ? 'progress_activity' : 'activity_circle'}
                          className="text-[16px]"
                          spin={verify === 'testing'}
                        />
                      </button>
                      {canEdit && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (model.isCustom) openEditCustomModal(model);
                            else openEditKeyModal(model.providerId);
                          }}
                          className={BTN_ICON}
                          title={t('Edit model')}
                          aria-label={t('Edit model')}
                        >
                          <LegacyIcon name="edit" className="text-[16px]" />
                        </button>
                      )}
                      {canRemove && (
                        <button
                          type="button"
                          disabled={deletingModelId === model.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            void handleRemoveModel(model.id, model.name);
                          }}
                          className={`${BTN_ICON} hover:bg-rose-50 text-red-500 hover:text-red-700 disabled:opacity-50`}
                          title={t('Remove model')}
                          aria-label={t('Remove model')}
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
              {t('Import CC Switch providers into Clutch (built-in agent credentials only).')}{' '}
              <button
                type="button"
                disabled={syncingCcSwitch}
                onClick={() => void handleRehydrateCcSwitch()}
                className="font-bold text-primary hover:underline disabled:opacity-50"
              >
                {syncingCcSwitch ? t('Importing…') : t('Import models')}
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
        </>
        ) : null}
    </SettingsPageShell>

      {activeModal && (
        <div className="fixed inset-0 bg-neutral-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-surface-bright rounded-xl shadow-lg border border-outline max-w-lg w-full max-h-[85vh] flex flex-col overflow-hidden">
            <div className="h-14 border-b border-outline/60 px-5 flex items-center justify-between flex-shrink-0 bg-surface-container/40">
              <h3 className="text-xs font-bold text-on-surface">
                {activeModal.type === 'add'
                  ? activeModal.modelKind === 'chat'
                    ? t('Add text model')
                    : activeModal.modelKind === 'image'
                      ? t('Add image model')
                      : t('Add video model')
                  : activeModal.type === 'edit-key'
                    ? t('Update API key')
                    : t('Edit custom model')}
              </h3>
              <button type="button" onClick={closeModal} className={BTN_ICON} aria-label={t('Cancel')}>
                <LegacyIcon name="close" className="text-[18px]" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4 text-left">
              {error && (
                <p className="text-xs text-rose-800 bg-rose-50 border border-rose-100 rounded-xl px-3 py-2">
                  {error}
                </p>
              )}

              {activeModal.type === 'add' && addModelKind && (
                <form id="models-add-form" onSubmit={(e) => void handleAddModel(e)} className="space-y-4">
                  <p className="text-[11px] text-on-surface-variant">
                    {addModelProviderId === 'custom'
                      ? t('Custom gateway — non-built-in model. Fill in the endpoint details below.')
                      : t('Built-in provider — enter your API key to enable this model.')}
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                        {t('Provider')}
                      </label>
                      <select
                        value={addModelProviderId}
                        onChange={(e) => {
                          const next = e.target.value;
                          setAddModelProviderId(next);
                          setAddModelApiKey('');
                          setError(null);
                          if (next === 'opencode') {
                            applyOpencodeProviderDefaults();
                          } else {
                            resetOpencodeForm();
                          }
                          setShowApiKey(false);
                        }}
                        className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface"
                      >
                        {providersForModelKind(addModelKind).map((id) => (
                          <option key={id} value={id}>
                            {PROVIDER_LABELS[id] ?? id}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                        {t('API key')}
                      </label>
                      <div className="relative flex items-center">
                        <input
                          type={showApiKey ? 'text' : 'password'}
                          required
                          value={addModelApiKey}
                          onChange={(e) => {
                            setAddModelApiKey(e.target.value);
                            setError(null);
                            setOpencodeListMessage(null);
                          }}
                          placeholder="sk-••••••••"
                          autoComplete="off"
                          className="w-full text-xs border border-outline bg-surface rounded-lg pl-3 pr-10 py-2 font-mono text-on-surface"
                        />
                        <button
                          type="button"
                          disabled={!addModelApiKey}
                          onClick={() => setShowApiKey((visible) => !visible)}
                          className="absolute right-2 p-1 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low disabled:opacity-40 disabled:pointer-events-none"
                          aria-label={showApiKey ? t('Hide API key') : t('Show API key')}
                        >
                          <LegacyIcon name={showApiKey ? 'visibility' : 'visibility_off'} className="text-[18px]" />
                        </button>
                      </div>
                    </div>
                    {addModelKind === 'chat' && addModelProviderId === 'opencode' && renderOpencodeModelPicker()}
                    {addModelProviderId === 'custom' && (
                      <>
                        <div className="space-y-1 sm:col-span-2">
                          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                            {t('Base URL')}
                          </label>
                          <input
                            required
                            value={addModelCustomBaseUrl}
                            onChange={(e) => setAddModelCustomBaseUrl(e.target.value)}
                            placeholder={
                              addModelKind === 'chat'
                                ? 'https://api.example.com/v1'
                                : 'https://api.example.com'
                            }
                            className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono text-on-surface"
                          />
                        </div>
                        <div className="space-y-1 sm:col-span-2">
                          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                            {t('API model id')}
                          </label>
                          <input
                            required
                            value={addModelCustomApiModel}
                            onChange={(e) => setAddModelCustomApiModel(e.target.value)}
                            placeholder={AGNES_DEFAULTS[addModelKind].api_model}
                            className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono text-on-surface"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </form>
              )}

              {activeModal.type === 'edit-key' && (
                <form id="models-edit-key-form" onSubmit={(e) => void handleConnectProvider(e)} className="space-y-4">
                  <p className="text-[11px] text-on-surface-variant">
                    {t('Saved in Clutch and used for built-in models of this provider.')}
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                        {t('Provider')}
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
                        {t('API key')}
                      </label>
                      <div className="relative flex items-center">
                        <input
                          type={showApiKey ? 'text' : 'password'}
                          required
                          disabled={loadingKey}
                          value={apiKey}
                          onChange={(e) => {
                            setApiKey(e.target.value);
                            setError(null);
                            setOpencodeListMessage(null);
                          }}
                          placeholder={loadingKey ? t('Loading…') : 'sk-••••••••'}
                          className="w-full text-xs border border-outline bg-surface rounded-lg pl-3 pr-10 py-2 font-mono text-on-surface disabled:opacity-60"
                        />
                        <button
                          type="button"
                          disabled={loadingKey || !apiKey}
                          onClick={() => setShowApiKey((visible) => !visible)}
                          className={`${BTN_GHOST} absolute right-1 top-1/2 -translate-y-1/2 z-10 p-1 border-0 text-on-surface-variant hover:text-on-surface hover:bg-transparent disabled:opacity-40`}
                          aria-label={showApiKey ? t('Hide API key') : t('Show API key')}
                        >
                          <LegacyIcon name={showApiKey ? 'visibility' : 'visibility_off'} className="text-[18px]" />
                        </button>
                      </div>
                    </div>
                    {providerId === 'opencode' && renderOpencodeModelPicker()}
                  </div>
                </form>
              )}

              {activeModal.type === 'edit-custom' && (
                <form id="models-edit-custom-form" onSubmit={(e) => void handleEditCustomModel(e)} className="space-y-4">
                  <p className="text-[11px] text-on-surface-variant">
                    {t('Custom gateway — non-built-in model. Fill in the endpoint details below.')}
                  </p>
                  <div className="space-y-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                        {t('Base URL')}
                      </label>
                      <input
                        required
                        value={editCustomBaseUrl}
                        onChange={(e) => setEditCustomBaseUrl(e.target.value)}
                        placeholder={
                          activeModal.modelKind === 'chat'
                            ? 'https://api.example.com/v1'
                            : 'https://api.example.com'
                        }
                        className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono text-on-surface"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                        {t('API model id')}
                      </label>
                      <input
                        required
                        value={editCustomApiModel}
                        onChange={(e) => setEditCustomApiModel(e.target.value)}
                        placeholder={AGNES_DEFAULTS[activeModal.modelKind].api_model}
                        className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono text-on-surface"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider block">
                        {t('API key (optional)')}
                      </label>
                      <input
                        type="password"
                        value={editCustomApiKey}
                        onChange={(e) => setEditCustomApiKey(e.target.value)}
                        placeholder="sk-••••••••"
                        className="w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 font-mono text-on-surface"
                      />
                    </div>
                  </div>
                </form>
              )}
            </div>

            <div className="border-t border-outline/60 px-5 py-4 flex items-center justify-end gap-2 flex-shrink-0">
              <button type="button" onClick={closeModal} className={`${BTN_GHOST} text-[10.5px]`}>
                {t('Cancel')}
              </button>
                {activeModal.type === 'add' && (
                  <button
                    type="submit"
                    form="models-add-form"
                    disabled={savingAddModel}
                    className={`${BTN_PRIMARY} text-[10.5px] disabled:opacity-50`}
                  >
                    {savingAddModel ? t('Saving…') : t('Save')}
                  </button>
                )}
                {activeModal.type === 'edit-key' && (
                  <button
                    type="submit"
                    form="models-edit-key-form"
                    disabled={savingKey}
                    className={`${BTN_PRIMARY} text-[10.5px] disabled:opacity-50`}
                  >
                    {savingKey ? t('Saving…') : t('Save')}
                  </button>
                )}
                {activeModal.type === 'edit-custom' && (
                  <button
                    type="submit"
                    form="models-edit-custom-form"
                    disabled={savingEditModel}
                    className={`${BTN_PRIMARY} text-[10.5px] disabled:opacity-50`}
                  >
                    {savingEditModel ? t('Saving…') : t('Save')}
                  </button>
                )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
