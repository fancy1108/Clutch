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
    cmd: 'curl https://cursor.com/install -fsS | bash',
    desc: 'Install Cursor Agent CLI (binary: cursor-agent / agent). Requires ~/.local/bin on PATH.',
    url: 'https://cursor.com',
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
  'mimo-cli': {
    cmd: 'curl -fsSL https://mimo.xiaomi.com/install | bash',
    desc: 'Install MiMo Code CLI (binary: mimo). Alternative: npm install -g @mimo-ai/cli',
    url: 'https://mimo.xiaomi.com/mimocode',
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
  'codebuddy-cli': {
    cmd: 'npm install -g @tencent-ai/codebuddy-code',
    desc: 'Install Tencent Cloud CodeBuddy CLI globally via npm (binary: codebuddy / cbc).',
    url: 'https://www.codebuddy.ai/docs/cli/installation',
  },
  'zcode-cli': {
    cmd: 'ln -sf /Applications/ZCode.app/Contents/Resources/glm/zcode.cjs ~/.local/bin/zcode && chmod +x ~/.local/bin/zcode',
    desc: 'Install ZCode desktop app first, then expose the bundled Node CJS entry as `zcode` on your PATH. Config: ~/.zcode/cli/config.json (see docs).',
    url: 'https://zcode.z.ai',
  },
  'qoder-cli': {
    cmd: 'curl -fsSL https://qoder.com/install | bash',
    desc: 'Install Qoder CLI (binary: qodercli). Requires ~/.local/bin on PATH.',
    url: 'https://qoder.com',
  },
  'comate-cli': {
    cmd: 'curl -fsSL https://comate.baidu.com/install | bash',
    desc: 'Install Baidu Comate CLI (binary: comate). AI coding assistant with chat subcommand.',
    url: 'https://comate.baidu.com',
  },
  'devin-cli': {
    cmd: 'curl -fsSL https://devin.ai/install | bash',
    desc: 'Install Devin CLI (binary: devin). Fast, minimal AI agent with -p/--print mode.',
    url: 'https://devin.ai',
  },
  'copilot-cli': {
    cmd: 'npm install -g @github/copilot',
    desc: 'Install GitHub Copilot CLI globally via npm.',
    url: 'https://github.com/features/copilot/cli',
  },
  'trae-cli': {
    cmd: 'curl -fsSL https://docs.trae.cn/cli/install | bash',
    desc: 'Install Trae CLI (binary: traecli). Supports -p/--print, --yolo, --resume.',
    url: 'https://docs.trae.cn/cli',
  },
};

/** CLIs tested in Clutch — primary install recommendations (Settings + onboarding). */
export const RECOMMENDED_CLI_IDS = ['codebuddy-cli', 'cursor-cli', 'mimo-cli', 'opencode-cli', 'claude-cli', 'ollama-cli', 'codex-cli', 'agy-cli', 'zcode-cli', 'qoder-cli', 'comate-cli', 'devin-cli', 'copilot-cli', 'trae-cli'] as const;

export const ONBOARDING_RECOMMENDED_CLI_IDS = RECOMMENDED_CLI_IDS;

export function installGuideForTool(toolId: string, toolName: string): CliInstallGuide {
  return (
    CLI_INSTALL_GUIDES[toolId] ?? {
      cmd: `npm install -g ${toolId.replace(/-cli$/, '')}`,
      desc: `Install ${toolName} globally.`,
    }
  );
}
