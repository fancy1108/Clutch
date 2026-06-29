import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Info, Loader2 } from 'lucide-react';

import { useLanguage } from '../../LanguageContext';
import { CliInstallGuideCard } from '../CliInstallGuideCard';
import { ensureAgentForConnectedTool } from '../../../services/agentProvisioning';
import { ONBOARDING_RECOMMENDED_CLI_IDS } from '../../../services/cliInstallGuides';
import { connectTool, fetchToolsStatus, type AiToolStatus } from '../../../services/toolsApi';
import { AiToolIcon } from '../../AiToolIcon';
import { BTN_GHOST, BTN_PRIMARY } from '../../ui/buttonStyles';

interface ToolsStepProps {
  modelReady: boolean;
  toolsReady: boolean;
  onToolsReady: (ready: boolean) => void;
  onAgentProvisioned: (agentId: string, agentName: string) => void;
  onSkip: () => void;
  /** Dev-only: force empty scan for UI preview (`?dev_tools_empty=1`). */
  debugForceEmpty?: boolean;
}

const MOCK_UNINSTALLED_TOOLS: AiToolStatus[] = [
  {
    id: 'claude-cli',
    name: 'Claude Code CLI',
    description: 'Terminal-based Claude Code for scripting and local agent execution.',
    icon: 'claude',
    kind: 'cli',
    installed: false,
    connected: false,
    registered: false,
    path: '',
    agentType: 'claude-cli',
  },
  {
    id: 'ollama-cli',
    name: 'Ollama',
    description: 'Run open-source LLMs locally via the Ollama CLI.',
    icon: 'ollama',
    kind: 'cli',
    installed: false,
    connected: false,
    registered: false,
    path: '',
    agentType: 'ollama-cli',
  },
  {
    id: 'aider-cli',
    name: 'Aider CLI',
    description: 'AI pair programming in your terminal.',
    icon: 'aider',
    kind: 'cli',
    installed: false,
    connected: false,
    registered: false,
    path: '',
    agentType: 'aider-cli',
  },
  {
    id: 'codex-cli',
    name: 'Codex CLI',
    description: 'Codex command-line coding agent.',
    icon: 'codex',
    kind: 'cli',
    installed: false,
    connected: false,
    registered: false,
    path: '',
    agentType: 'codex-cli',
  },
];

export function ToolsStep({
  modelReady,
  toolsReady,
  onToolsReady,
  onAgentProvisioned,
  onSkip,
  debugForceEmpty = false,
}: ToolsStepProps) {
  const { t } = useLanguage();
  const [tools, setTools] = useState<AiToolStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [provisionNote, setProvisionNote] = useState<string | null>(null);
  const [ollamaNoModel, setOllamaNoModel] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (debugForceEmpty) {
        setTools(MOCK_UNINSTALLED_TOOLS);
        onToolsReady(false);
        return;
      }
      const list = await fetchToolsStatus();
      setTools(list);
      const ready = list.some((tool) => tool.installed && tool.connected);
      onToolsReady(ready);
    } catch {
      setTools([]);
      setError(t('Sidecar unavailable — start the orchestrator'));
    } finally {
      setLoading(false);
    }
  }, [debugForceEmpty, onToolsReady, t]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleConnect = async (tool: AiToolStatus) => {
    setPendingId(tool.id);
    setError(null);
    setProvisionNote(null);
    setOllamaNoModel(false);
    try {
      await connectTool(tool.id);
      const list = await fetchToolsStatus();
      setTools(list);
      const connected = list.find((item) => item.id === tool.id);
      const ready = list.some((item) => item.installed && item.connected);
      onToolsReady(ready);
      if (connected) {
        const agent = await ensureAgentForConnectedTool(connected);
        if (agent) {
          onAgentProvisioned(agent.id, agent.name);
          setProvisionNote(t('Onboarding agent created').replace('{name}', agent.name));
        } else if (connected.agentType === 'ollama-cli' || connected.id === 'ollama-cli') {
          setOllamaNoModel(true);
        }
      }
    } catch {
      setError(t('Failed to connect tool'));
    } finally {
      setPendingId(null);
    }
  };

  const installed = tools.filter((tool) => tool.installed);
  const notInstalled = tools.filter((tool) => !tool.installed);
  const noCliInstalled = !loading && installed.length === 0 && tools.length > 0;

  const recommendedGuides = useMemo(() => {
    return ONBOARDING_RECOMMENDED_CLI_IDS.map((id) => notInstalled.find((tool) => tool.id === id)).filter(
      (tool): tool is AiToolStatus => Boolean(tool),
    );
  }, [notInstalled]);

  const otherGuides = useMemo(() => {
    const recommendedIds = new Set<string>(ONBOARDING_RECOMMENDED_CLI_IDS);
    return notInstalled.filter((tool) => !recommendedIds.has(tool.id));
  }, [notInstalled]);

  return (
    <div className="space-y-5">
      <div className="text-center">
        <h2 className="text-xl font-bold text-neutral-900">{t('Connect local CLI tools')}</h2>
        <p className="mt-2 text-sm text-neutral-500 max-w-md mx-auto">
          {t('If you verified a cloud model above, you can skip; otherwise connect at least one CLI.')}
        </p>
      </div>

      <div className="flex justify-center">
        <button type="button" onClick={() => void refresh()} disabled={loading} className={`${BTN_GHOST} text-[10px]`}>
          {t('Rescan')}
        </button>
      </div>

      {loading ? (
        <p className="text-xs text-neutral-400 text-center italic">{t('Scanning local toolchains…')}</p>
      ) : noCliInstalled ? (
        <div className="space-y-4 max-w-md mx-auto">
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/80 p-4 flex items-start gap-3 text-left">
            <Info className="h-5 w-5 shrink-0 text-indigo-600 mt-0.5" aria-hidden />
            <div className="space-y-1.5">
              <p className="text-xs font-bold text-indigo-950">{t('No AI command-line tools detected yet')}</p>
              <p className="text-[11px] text-indigo-900/90 leading-relaxed">
                {t('Install at least one recommended tool below (e.g. Claude Code, Ollama, or Aider). After installing in Terminal, click Rescan, then Connect. If you configured a cloud model, you can skip this step after verifying it.')}
              </p>
              <p className="text-[10px] text-indigo-800/80">
                {t('Run a command below in Terminal, then return here and click Rescan.')}
              </p>
            </div>
          </div>

          <div className="text-left space-y-2">
            <p className="text-[11px] font-bold text-neutral-800">{t('Recommended to install')}</p>
            {recommendedGuides.map((tool, index) => (
              <CliInstallGuideCard key={tool.id} tool={tool} defaultExpanded={index === 0} />
            ))}
          </div>

          {otherGuides.length > 0 ? (
            <div className="text-left space-y-2">
              <p className="text-[11px] font-semibold text-neutral-600">{t('More CLI options')}</p>
              {otherGuides.map((tool) => (
                <CliInstallGuideCard key={tool.id} tool={tool} />
              ))}
            </div>
          ) : null}
        </div>
      ) : installed.length === 0 ? (
        <p className="text-xs text-neutral-500 text-center">{t('Onboarding no cli installed')}</p>
      ) : (
        <div className="space-y-2">
          {installed.map((tool) => (
            <div
              key={tool.id}
              className="flex items-center gap-3 rounded-xl border border-neutral-200 px-3 py-2.5 bg-white"
            >
              <AiToolIcon tool={tool} />
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-bold text-neutral-800">{tool.name}</p>
                <p className="text-[10px] text-neutral-500 truncate">{tool.description}</p>
              </div>
              {tool.connected ? (
                <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {t('Connected')}
                </span>
              ) : (
                <button
                  type="button"
                  data-testid={`onboarding-connect-${tool.id}`}
                  disabled={pendingId === tool.id}
                  onClick={() => void handleConnect(tool)}
                  className={`${BTN_PRIMARY} text-[10px] px-2.5 py-1`}
                >
                  {pendingId === tool.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t('Connect')}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {provisionNote && (
        <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-center">
          {provisionNote}
        </p>
      )}

      {ollamaNoModel && (
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-center">
          {t('Onboarding ollama no models')}
        </p>
      )}

      {error && (
        <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2 text-center">{error}</p>
      )}

      {modelReady && (
        <div className="flex justify-center">
          <button type="button" data-testid="onboarding-tools-skip" onClick={onSkip} className={BTN_GHOST}>
            {t('Skip for now')}
          </button>
        </div>
      )}
    </div>
  );
}
