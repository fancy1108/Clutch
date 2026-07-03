import type { MainView } from '../types';
import type { AgentCapabilityTabId } from './agentCapabilityTiers';
import { SIDECAR_BASE as BASE, sidecarFetch } from './sidecarUrl';

export const SETTINGS_AGENT_TAB_KEY = 'clutch.settings.agentCapabilityTab';

export type CliConfigProvider = {
  id: string;
  name: string;
  app_type: string;
  model_id: string | null;
  is_active: boolean;
};

export type CliAuthProvider = {
  id: string;
  name: string;
  auth_type: string;
  has_credential: boolean;
};

export type CliModelsScan = {
  agent_type: string;
  cc_switch_found: boolean;
  cc_switch_cli_available: boolean;
  active_provider_id: string | null;
  active_model_id: string | null;
  base_url?: string | null;
  default_agent?: string | null;
  providers: CliConfigProvider[];
  auth_providers?: CliAuthProvider[];
  catalog?: Array<{
    provider: string;
    model_id: string;
    name: string;
    model_ref?: string;
    is_builtin?: boolean;
  }>;
  available_models?: Array<{
    provider: string;
    model_id: string;
    name: string;
    model_ref: string;
    is_builtin?: boolean;
  }>;
  config_paths?: string[];
  auth_path?: string | null;
  model_state_path?: string | null;
  settings_path?: string;
  env_preview?: Record<string, string>;
  opencode_cli_available?: boolean;
};

export type CliSkillScanItem = {
  key: string;
  label: string;
  desc: string;
  source: string;
};

export type CliMcpScanItem = {
  name: string;
  transport: string;
  endpoint: string;
  source: string;
  enabled_for_agent?: boolean;
};

export function stashSettingsAgentTab(tab: AgentCapabilityTabId): void {
  sessionStorage.setItem(SETTINGS_AGENT_TAB_KEY, tab);
}

export function consumeSettingsAgentTab(): AgentCapabilityTabId | null {
  const raw = sessionStorage.getItem(SETTINGS_AGENT_TAB_KEY);
  sessionStorage.removeItem(SETTINGS_AGENT_TAB_KEY);
  if (raw === 'clutch' || raw === 'claude-cli' || raw === 'opencode-cli' || raw === 'more') {
    return raw;
  }
  return null;
}

export function openSettingsWithAgentTab(view: MainView, agentTab: AgentCapabilityTabId): void {
  stashSettingsAgentTab(agentTab);
  window.dispatchEvent(new CustomEvent('clutch-navigate-settings', { detail: { view } }));
}

async function parseJson<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      typeof body?.detail?.message === 'string'
        ? body.detail.message
        : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return body as T;
}

export async function fetchCliModelsConfig(agentType: string): Promise<CliModelsScan> {
  const response = await sidecarFetch(`${BASE}/api/cli-config/${encodeURIComponent(agentType)}/models`);
  return parseJson(response);
}

export async function fetchCliSkillsConfig(agentType: string): Promise<{
  agent_type: string;
  skills: CliSkillScanItem[];
  roots: string[];
}> {
  const response = await sidecarFetch(`${BASE}/api/cli-config/${encodeURIComponent(agentType)}/skills`);
  return parseJson(response);
}

export async function fetchCliMcpConfig(agentType: string): Promise<{
  agent_type: string;
  servers: CliMcpScanItem[];
  cc_switch_found: boolean;
  cc_switch_cli_available: boolean;
}> {
  const response = await sidecarFetch(`${BASE}/api/cli-config/${encodeURIComponent(agentType)}/mcp`);
  return parseJson(response);
}

export async function activateCliProvider(
  agentType: string,
  providerId: string,
): Promise<{ ok: boolean; message: string }> {
  const response = await sidecarFetch(
    `${BASE}/api/cli-config/${encodeURIComponent(agentType)}/activate-provider`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider_id: providerId }),
    },
  );
  return parseJson(response);
}

export async function activateCliModel(
  agentType: string,
  modelRef: string,
): Promise<{ ok: boolean; message: string }> {
  const response = await sidecarFetch(
    `${BASE}/api/cli-config/${encodeURIComponent(agentType)}/activate-model`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_ref: modelRef }),
    },
  );
  return parseJson(response);
}

export async function installCcSwitchCli(): Promise<{
  ok: boolean;
  message: string;
  cli_path?: string;
  method?: string;
}> {
  const response = await sidecarFetch(`${BASE}/api/cli-config/install-cc-switch-cli`, {
    method: 'POST',
  });
  return parseJson(response);
}

export async function prefetchCcSwitchCli(): Promise<{
  ok: boolean;
  cached?: boolean;
  already_installed?: boolean;
  path?: string;
  message?: string;
}> {
  const response = await sidecarFetch(`${BASE}/api/cli-config/prefetch-cc-switch-cli`, {
    method: 'POST',
  });
  return parseJson(response);
}
