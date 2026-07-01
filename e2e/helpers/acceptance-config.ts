import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const e2eRoot = join(dirname(fileURLToPath(import.meta.url)), '..');

export type AcceptanceConfig = {
  workflow: {
    id: string;
    fixture_path: string;
    agents_fixture_path: string;
    start_instruction: string;
    timeout_minutes: number;
  };
  api_models: {
    text_model_id: string;
    text_provider_id: string;
    text_env_key: string;
    image_model_id: string;
    image_provider_id: string;
    image_env_key: string;
  };
  cli_exclude: string[];
  cli_timeout_ms: number;
  cross_agent_cli_timeout_ms: number;
  api_timeout_ms: number;
  ollama_timeout_ms: number;
  test_timeouts_ms: {
    default_test: number;
    ui: number;
    cli_turn: number;
    api_turn: number;
    ollama_multi: number;
    image: number;
    cross_agent: number;
    workflow: number;
    sidecar_health: number;
    tauri_boot: number;
    suite_global: number;
  };
};

export type AcceptanceManifest = {
  cli_tools: string[];
  cli_skipped: string[];
  ollama_tags: string[];
  text_model_id: string;
  image_model_id: string;
  text_key_present: boolean;
  image_key_present: boolean;
  workflow_id: string;
  start_instruction: string;
};

export function loadAcceptanceConfig(): AcceptanceConfig {
  const raw = readFileSync(join(e2eRoot, 'acceptance.config.json'), 'utf8');
  return JSON.parse(raw) as AcceptanceConfig;
}

export function loadAcceptanceManifest(): AcceptanceManifest {
  const path = process.env.CLUTCH_E2E_ACCEPTANCE_MANIFEST;
  if (!path) {
    throw new Error('CLUTCH_E2E_ACCEPTANCE_MANIFEST is not set');
  }
  return JSON.parse(readFileSync(path, 'utf8')) as AcceptanceManifest;
}

export function cliAgentId(toolId: string): string {
  return `agent-e2e-cli-${toolId}`;
}

export function ollamaModelId(tag: string): string {
  const slug = tag.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return slug ? `ollama-local-${slug}` : 'ollama-local-unknown';
}
