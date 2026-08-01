import { useCallback, useEffect, useMemo, useState } from 'react';
import { THEME_PRESETS, type ThemePresetId } from '../components/ThemeManager';
import { DEFAULT_FONT_SIZE, type AppFontSize } from '../services/fontSizePreference';
import { setUserChatAvatar } from '../services/clutchState';
import {
  fetchModelsConfig,
  mapModelConfigToUi,
  saveModelsConfig,
} from '../services/modelsApi';
import {
  fetchPermissionMode,
  savePermissionMode,
  type PermissionMode,
} from '../services/permissionApi';
import {
  fetchPreferences,
  saveFontSizePreference,
  saveThemePreference,
  saveUserNamePreference,
} from '../services/themeApi';

export type ConfiguredModelUi = {
  id: string;
  name: string;
  provider: string;
  providerId: string;
  modelKind?: 'chat' | 'image' | 'video';
  contextWindow: string;
  temperature: number;
  sourceSummary: string;
  credentialSourceLabel: string | null;
  available?: boolean;
};

type UseAppSettingsOptions = {
  t: (key: string) => string;
  isTurnInProgress: boolean;
  onModelSwitchError: (message: string) => void;
};

export function useAppSettings({ t, isTurnInProgress, onModelSwitchError }: UseAppSettingsOptions) {
  const [themeId, setThemeIdState] = useState<ThemePresetId>('pristine-light');
  const [fontSize, setFontSizeState] = useState<AppFontSize>(DEFAULT_FONT_SIZE);
  const [userAvatar, setUserAvatarState] = useState<string>('');
  const [userName, setUserNameState] = useState<string>('User');

  const [selectedModel, setSelectedModel] = useState<string>('');
  const [activeModelId, setActiveModelId] = useState<string>('');
  const [configuredModels, setConfiguredModels] = useState<ConfiguredModelUi[]>([]);
  const [pendingFooterModelId, setPendingFooterModelId] = useState<string | null>(null);
  const [modelMenuOpen, setModelMenuOpen] = useState(false);

  const [permissionMode, setPermissionMode] = useState<PermissionMode>('auto_edit');

  useEffect(() => {
    void fetchPreferences()
      .then((prefs) => {
        setThemeIdState(prefs.active_theme_id);
        setFontSizeState(prefs.font_size ?? DEFAULT_FONT_SIZE);
        if (prefs.user_avatar) {
          setUserAvatarState(prefs.user_avatar);
          setUserChatAvatar(prefs.user_avatar);
        }
        if (prefs.user_name) {
          setUserNameState(prefs.user_name);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    void fetchPermissionMode()
      .then((mode) => setPermissionMode(mode))
      .catch(() => {});
  }, []);

  const setThemeId = useCallback((id: string) => {
    const preset = THEME_PRESETS.find((item) => item.id === id);
    if (!preset) return;
    setThemeIdState(preset.id as ThemePresetId);
    void saveThemePreference(preset.id as ThemePresetId).catch(() => {});
  }, []);

  const setFontSize = useCallback((size: AppFontSize) => {
    setFontSizeState(size);
    void saveFontSizePreference(size).catch(() => {});
  }, []);

  const setUserName = useCallback((name: string) => {
    setUserNameState(name);
    void saveUserNamePreference(name).catch(() => {});
  }, []);

  const syncModelsConfig = useCallback(async () => {
    const config = await fetchModelsConfig();
    const mapped = mapModelConfigToUi(config);
    setConfiguredModels(mapped.models);
    setActiveModelId(mapped.activeModelId);
    const active = mapped.models.find((m) => m.id === mapped.activeModelId);
    setSelectedModel(active?.name ?? '');
    return mapped;
  }, []);

  useEffect(() => {
    void syncModelsConfig().catch(() => {});
  }, [syncModelsConfig]);

  useEffect(() => {
    if (isTurnInProgress || !pendingFooterModelId) return;
    const modelId = pendingFooterModelId;
    setPendingFooterModelId(null);
    void (async () => {
      try {
        await saveModelsConfig({ active_model_id: modelId });
        await syncModelsConfig();
      } catch (error) {
        console.error('[Clutch] deferred model switch failed:', error);
        onModelSwitchError(
          error instanceof Error ? error.message : t('Failed to switch model.'),
        );
        await syncModelsConfig().catch(() => {});
      }
    })();
  }, [isTurnInProgress, pendingFooterModelId, syncModelsConfig, t, onModelSwitchError]);

  const handlePermissionModeChange = useCallback((mode: PermissionMode) => {
    setPermissionMode(mode);
    void savePermissionMode(mode).catch(() => {});
  }, []);

  const closeModelMenu = useCallback(() => setModelMenuOpen(false), []);

  const toggleModelMenu = useCallback(() => {
    setModelMenuOpen((open) => {
      const next = !open;
      if (next) {
        void syncModelsConfig().catch(() => {});
      }
      return next;
    });
  }, [syncModelsConfig]);

  const handleFooterModelSelect = useCallback((modelId: string) => {
    const model = configuredModels.find((item) => item.id === modelId);
    if (!model) return;
    setModelMenuOpen(false);
    setActiveModelId(modelId);
    setSelectedModel(model.name);
    if (isTurnInProgress) {
      setPendingFooterModelId(modelId);
      return;
    }
    void (async () => {
      try {
        await saveModelsConfig({ active_model_id: modelId });
        await syncModelsConfig();
      } catch (error) {
        console.error('[Clutch] model switch failed:', error);
        onModelSwitchError(
          error instanceof Error ? error.message : t('Failed to switch model.'),
        );
        await syncModelsConfig().catch(() => {});
      }
    })();
  }, [configuredModels, isTurnInProgress, syncModelsConfig, t, onModelSwitchError]);

  const currentThemeObj = useMemo(
    () => THEME_PRESETS.find((item) => item.id === themeId) || THEME_PRESETS[0],
    [themeId],
  );
  const themeVars = currentThemeObj.variables;

  return {
    themeId,
    fontSize,
    userAvatar,
    setUserAvatar: setUserAvatarState,
    userName,
    setUserName,
    setThemeId,
    setFontSize,
    selectedModel,
    setSelectedModel,
    activeModelId,
    setActiveModelId,
    configuredModels,
    setConfiguredModels,
    permissionMode,
    handlePermissionModeChange,
    syncModelsConfig,
    modelMenuOpen,
    setModelMenuOpen,
    closeModelMenu,
    toggleModelMenu,
    handleFooterModelSelect,
    themeVars,
  };
}
