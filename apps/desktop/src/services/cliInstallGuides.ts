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
  'rivet-cli': {
    cmd: 'npm install -g tianshu-tui',
    desc: 'Install Tianshu (天枢) Rivet CLI globally via npm.',
  },
  'opencode-cli': {
    cmd: 'npm install -g opencode-ai@latest',
    desc: 'Install OpenCode AI coding agent globally via npm (binary: opencode).',
    url: 'https://opencode.ai',
  },
  'amazon-q-cli': {
    cmd: 'brew install amazon-q',
    desc: 'Install legacy Amazon Q Developer CLI (binary: q). Superseded by Kiro CLI.',
  },
  'amp-cli': {
    cmd: 'npm install -g @ampcode/cli',
    desc: 'Install Sourcegraph Amp coding agent globally via npm.',
    url: 'https://ampcode.com',
  },
  'continue-cli': {
    cmd: 'npm install -g @continuedev/cli',
    desc: 'Install Continue CLI (binary: cn) globally via npm.',
    url: 'https://continue.dev',
  },
  'copilot-cli': {
    cmd: 'npm install -g @github/copilot',
    desc: 'Install GitHub Copilot CLI globally via npm.',
    url: 'https://github.com/features/copilot/cli',
  },
  'crush-cli': {
    cmd: 'brew install charmbracelet/tap/crush',
    desc: 'Install Charm Crush AI coding TUI (or: npm install -g @charmland/crush).',
    url: 'https://github.com/charmbracelet/crush',
  },
  'droid-cli': {
    cmd: 'curl -fsSL https://app.factory.ai/cli | sh',
    desc: 'Install Factory Droid CLI (binary: droid). Alternative: npm install -g droid.',
    url: 'https://factory.ai',
  },
  'goose-cli': {
    cmd: 'curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | bash',
    desc: 'Install Goose AI agent CLI (AAIF).',
    url: 'https://goose-docs.ai',
  },
  'gptme-cli': {
    cmd: 'pip install gptme',
    desc: 'Install gptme terminal AI assistant via pip (or: pipx install gptme).',
    url: 'https://gptme.ai',
  },
  'kiro-cli': {
    cmd: 'curl -fsSL https://cli.kiro.dev/install | bash',
    desc: 'Install Kiro CLI (successor to Amazon Q Developer).',
    url: 'https://kiro.dev/cli',
  },
  'openclaw-cli': {
    cmd: 'npm install -g openclaw@latest',
    desc: 'Install OpenClaw AI agent CLI globally via npm.',
    url: 'https://openclaw.ai',
  },
  'qwen-code-cli': {
    cmd: 'npm install -g @qwen-code/qwen-code@latest',
    desc: 'Install Qwen Code AI coding agent globally via npm (requires Node.js 22+).',
    url: 'https://github.com/QwenLM/qwen-code',
  },
};

/** CLIs tested in Clutch — primary install recommendations (Settings + onboarding). */
export const RECOMMENDED_CLI_IDS = ['opencode-cli', 'claude-cli', 'ollama-cli', 'codex-cli', 'agy-cli'] as const;

export const ONBOARDING_RECOMMENDED_CLI_IDS = RECOMMENDED_CLI_IDS;

export function installGuideForTool(toolId: string, toolName: string): CliInstallGuide {
  return (
    CLI_INSTALL_GUIDES[toolId] ?? {
      cmd: `npm install -g ${toolId.replace(/-cli$/, '')}`,
      desc: `Install ${toolName} globally.`,
    }
  );
}
