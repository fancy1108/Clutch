/** Shared CLI install copy for Settings → Tools and onboarding. */

export interface CliInstallGuide {
  cmd: string;
  desc: string;
  url?: string;
}

export const CLI_INSTALL_GUIDES: Record<string, CliInstallGuide> = {
  'claude-cli': {
    cmd: 'npm install -g @anthropic-ai/claude-code',
    desc: 'Install Claude Code globally via npm (requires Node.js 18+).',
  },
  'agy-cli': {
    cmd: 'npm install -g antigravity-cli',
    desc: 'Install Antigravity CLI tool globally via npm.',
  },
  'codex-cli': {
    cmd: 'npm install -g openai-codex',
    desc: 'Install OpenAI Codex CLI tool globally via npm.',
  },
  'code-cli': {
    cmd: 'code',
    desc: 'Open VS Code, press Cmd+Shift+P, and run "Shell Command: Install \'code\' command in PATH".',
  },
  'codeium-cli': {
    cmd: 'npm install -g codeium-cli',
    desc: 'Install Codeium command line interface via npm.',
  },
  'aider-cli': {
    cmd: 'pip install aider-chat',
    desc: 'Install Aider AI pair programmer via Python pip.',
  },
  'gemini-cli': {
    cmd: 'npm install -g gemini-cli',
    desc: 'Install Google Gemini CLI tool globally via npm.',
  },
  'ollama-cli': {
    cmd: 'curl -fsSL https://ollama.com/install.sh | sh',
    desc: 'Download and install Ollama for local LLMs, or install from ollama.com.',
    url: 'https://ollama.com',
  },
  'cursor-cli': {
    cmd: 'cursor',
    desc: 'Open Cursor IDE, press Cmd+Shift+P, and run "Shell Command: Install \'cursor\' command in PATH".',
  },
};

/** Shown first on onboarding when no CLI is detected. */
export const ONBOARDING_RECOMMENDED_CLI_IDS = ['claude-cli', 'ollama-cli', 'aider-cli'] as const;

export function installGuideForTool(toolId: string, toolName: string): CliInstallGuide {
  return (
    CLI_INSTALL_GUIDES[toolId] ?? {
      cmd: `npm install -g ${toolId.replace(/-cli$/, '')}`,
      desc: `Install ${toolName} globally.`,
    }
  );
}
