/** Brand logos for AI tools / agent engines — single resolver for Agent, Tool, Flow, Chat. */

import type { Agent } from '../types';
import { agentTypeFromAgent, isClutchAgentType, type AgentTypeId } from './agentTypes';

import chatgptLogo from '../assets/tool-logos/chatgpt.svg';
import aiderLogo from '../assets/tool-logos/aider.svg';
import antigravityLogo from '../assets/tool-logos/antigravity.svg';
import claudeLogo from '../assets/tool-logos/claude.svg';
import ollamaLogo from '../assets/tool-logos/ollama.svg';
import vscodeLogo from '../assets/tool-logos/vscode.svg';

/** Only tools with an explicit asset in assets/tool-logos/. */
export type BrandLogoKey =
  | 'claude-cli'
  | 'antigravity-cli'
  | 'codex-cli'
  | 'ollama-cli'
  | 'aider-cli'
  | 'code-cli';

const BRAND_LOGO_SRC: Record<BrandLogoKey, string> = {
  'claude-cli': claudeLogo,
  'antigravity-cli': antigravityLogo,
  'codex-cli': chatgptLogo,
  'ollama-cli': ollamaLogo,
  'aider-cli': aiderLogo,
  'code-cli': vscodeLogo,
};

const ALIAS_TO_KEY: Record<string, BrandLogoKey> = {
  'claude-cli': 'claude-cli',
  'claude cli': 'claude-cli',
  'claude code cli': 'claude-cli',
  'claude code (local cli)': 'claude-cli',
  'antigravity-cli': 'antigravity-cli',
  'antigravity cli': 'antigravity-cli',
  'agy-cli': 'antigravity-cli',
  agy: 'antigravity-cli',
  'codex-cli': 'codex-cli',
  codex: 'codex-cli',
  'codex cli': 'codex-cli',
  'openai codex cli': 'codex-cli',
  'ollama-cli': 'ollama-cli',
  ollama: 'ollama-cli',
  'aider-cli': 'aider-cli',
  aider: 'aider-cli',
  'code-cli': 'code-cli',
  code: 'code-cli',
  'vs code cli': 'code-cli',
};

export function normalizeBrandLogoKey(
  raw: string | null | undefined,
): BrandLogoKey | null {
  const key = (raw ?? '').trim().toLowerCase();
  if (!key) return null;
  return ALIAS_TO_KEY[key] ?? null;
}

export function brandLogoSrcForKey(key: BrandLogoKey | null | undefined): string | undefined {
  if (!key) return undefined;
  return BRAND_LOGO_SRC[key];
}

export function resolveBrandLogoSrc(params: {
  toolId?: string | null;
  agentType?: AgentTypeId | string | null;
  aiTool?: string | null;
  runtimeEngine?: string | null;
  agent?: Pick<Agent, 'agentType' | 'aiEngine'> | null;
}): string | undefined {
  if (params.agent && isClutchAgentType(params.agent)) {
    return undefined;
  }
  const candidates = [
    params.toolId,
    params.aiTool,
    params.agentType,
    params.agent ? agentTypeFromAgent(params.agent) : null,
    params.runtimeEngine,
  ];
  for (const candidate of candidates) {
    const key = normalizeBrandLogoKey(candidate);
    const src = brandLogoSrcForKey(key);
    if (src) return src;
  }
  return undefined;
}

export function resolveAgentBrandLogo(agent: Pick<Agent, 'agentType' | 'aiEngine'> | null | undefined): string | undefined {
  return resolveBrandLogoSrc({ agent });
}

export function resolveToolBrandLogo(toolId: string | null | undefined): string | undefined {
  return resolveBrandLogoSrc({ toolId });
}

export function resolveWorkflowToolBrandLogo(aiTool: string | null | undefined): string | undefined {
  return resolveBrandLogoSrc({ aiTool });
}
