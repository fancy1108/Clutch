import React, { useCallback, useEffect, useState } from 'react';
import {
  connectTool,
  disconnectTool,
  fetchToolsStatus,
  autoConfigureTool,
  type AiToolStatus,
} from '../services/toolsApi';
import { CLI_INSTALL_GUIDES } from '../services/cliInstallGuides';
import { BTN_GHOST, BTN_PRIMARY } from './ui/buttonStyles';
import { SettingsPageHeader, SettingsPageShell } from './ui/SettingsPageHeader';
import { AiToolIcon } from './AiToolIcon';
import { ALERT_WARNING } from './ui/surfaceStyles';
import { LegacyIcon } from './ui/LegacyIcon';
import { useLanguage } from './LanguageContext';

interface AiToolsManagerProps {
  isModalStyle?: boolean;
}

const INSTALL_INSTRUCTIONS = CLI_INSTALL_GUIDES;

export default function AiToolsManager({ isModalStyle }: AiToolsManagerProps) {
  const { t } = useLanguage();
  const [tools, setTools] = useState<AiToolStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [expandedInstallId, setExpandedInstallId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchToolsStatus();
      setTools(list);
    } catch {
      setTools([]);
      setError(t('Sidecar unavailable — start the orchestrator to scan local tools.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleConnect = async (id: string) => {
    setPendingId(id);
    setError(null);
    try {
      await connectTool(id);
      await refresh();
    } catch {
      setError('Failed to connect tool. Ensure the CLI is installed and Sidecar is running.');
    } finally {
      setPendingId(null);
    }
  };

  const handleDisconnect = async (id: string) => {
    setPendingId(id);
    setError(null);
    try {
      await disconnectTool(id);
      await refresh();
    } catch {
      setError('Failed to disconnect tool.');
    } finally {
      setPendingId(null);
    }
  };

  const handleAutoConfigure = async (id: string) => {
    setPendingId(id);
    setError(null);
    try {
      await autoConfigureTool(id);
      await refresh();
    } catch (err: any) {
      setError(err?.message || 'Failed to auto-configure tool.');
    } finally {
      setPendingId(null);
    }
  };

  const connectedTools = tools.filter((t) => t.installed && t.connected);
  const availableTools = tools.filter((t) => t.installed && !t.connected);
  const notInstalledTools = tools.filter((t) => !t.installed);
  const isNoCliInstalled = tools.every((t) => !t.installed);

  return (
    <SettingsPageShell>
      <SettingsPageHeader
        isModalStyle={isModalStyle}
        icon="handyman"
        title={t('AI Tools Integration')}
        description={t('Detected local AI CLIs on this machine. Connect only tools you want Clutch to route to.')}
        descriptionSecondary={t('Install guides below list tested CLIs only; other whitelist tools appear here once installed.')}
        actions={
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading}
            className={`${BTN_GHOST} text-[10px] font-bold disabled:opacity-50`}
          >
            {t('Rescan')}
          </button>
        }
      />

        {error && (
          <p className={ALERT_WARNING}>{error}</p>
        )}

        {isNoCliInstalled && !loading && (
          <div className="p-4 rounded-xl bg-indigo-50/80 border border-indigo-100 flex items-start gap-3">
            <LegacyIcon name="info" className="text-indigo-500 w-5 h-5 mt-0.5 flex-shrink-0" />
            <div className="text-left text-xs text-indigo-900 leading-relaxed">
              <p className="font-bold text-indigo-950">{t('No AI command-line tools installed yet')}</p>
              <p className="mt-1 text-indigo-700/90">
                {t('To start utilizing agent-based coding, please install at least one tool (e.g. Claude Code, Ollama, Codex, or Antigravity) using the installation guides below, and then click connect.')}
              </p>
            </div>
          </div>
        )}

        {loading ? (
          <p className="text-xs text-neutral-400 italic">{t('Scanning local toolchains…')}</p>
        ) : tools.length === 0 ? (
          <div className="text-left space-y-2">
            <p className="text-xs text-neutral-500">{t('No supported AI tools detected on this machine.')}</p>
            <p className="text-[11px] text-neutral-400">
              {t('Install an AI CLI (e.g. claude, codex, agy, ollama), then rescan.')}
            </p>
          </div>
        ) : (
          <>
            <section className="text-left">
              <h3 className="text-xs font-bold text-neutral-900 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                {t('Connected')}
              </h3>
              {connectedTools.length === 0 ? (
                <p className="text-xs text-neutral-400 italic">{t('No AI tools connected yet.')}</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {connectedTools.map((tool) => (
                    <div key={tool.id} className="p-4 border border-neutral-200/60 rounded-xl bg-white shadow-xs flex items-start gap-4">
                      <AiToolIcon tool={tool} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <h4 className="text-xs font-bold text-neutral-800">{tool.name}</h4>
                          {!tool.registered && (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium bg-amber-50 text-amber-600 border border-amber-200">
                              <LegacyIcon name="warning" className="w-2.5 h-2.5" />
                              {t('Unconfigured')}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-neutral-500 mt-1 leading-relaxed">{tool.description}</p>
                        <div className="mt-1.5 flex items-center gap-1.5">
                          <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-neutral-400 bg-neutral-100 border border-neutral-200 px-1.5 py-0.5 rounded">
                            {tool.kind === 'cli' ? t('CLI') : t('Client')}
                          </span>
                          <span className="text-[9.5px] font-mono text-neutral-400 truncate" title={tool.path}>
                            {tool.path}
                          </span>
                        </div>
                        <div className="mt-3 flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() => void handleDisconnect(tool.id)}
                            disabled={pendingId !== null}
                            className="text-[10px] font-semibold text-neutral-400 hover:text-red-500 transition-colors disabled:opacity-50"
                          >
                            {pendingId === tool.id ? t('Disconnecting…') : t('Disconnect')}
                          </button>
                          {!tool.registered && (
                            <>
                              <span className="text-neutral-200 text-xs">|</span>
                              <button
                                type="button"
                                onClick={() => void handleAutoConfigure(tool.id)}
                                disabled={pendingId !== null}
                                className="text-[10px] font-semibold text-indigo-600 hover:text-indigo-800 transition-colors disabled:opacity-50 flex items-center gap-1"
                              >
                                {pendingId === tool.id ? (
                                  <>
                                    <LegacyIcon name="progress_activity" className="animate-spin w-3 h-3 text-indigo-500" />
                                    {t('Configuring…')}
                                  </>
                                ) : (
                                  <>
                                    <LegacyIcon name="bolt" className="w-3 h-3" />
                                    {t('Auto Config')}
                                  </>
                                )}
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="text-left">
              <h3 className="text-xs font-bold text-neutral-900 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-neutral-300"></span>
                {t('Detected (not connected)')}
              </h3>
              {availableTools.length === 0 ? (
                <p className="text-xs text-neutral-400 italic">{t('All detected tools are connected.')}</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {availableTools.map((tool) => (
                    <div key={tool.id} className="p-4 border border-dashed border-neutral-200 rounded-xl bg-neutral-50/50 flex items-start gap-4">
                      <AiToolIcon tool={tool} dimmed />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <h4 className="text-xs font-bold text-neutral-600">{tool.name}</h4>
                          {!tool.registered && (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium bg-amber-50 text-amber-600 border border-amber-200">
                              <LegacyIcon name="warning" className="w-2.5 h-2.5" />
                              {t('Unconfigured')}
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-neutral-400 mt-1 leading-relaxed">{tool.description}</p>
                        <div className="mt-1.5 flex items-center gap-1.5">
                          <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-neutral-400 bg-neutral-100 border border-neutral-200 px-1.5 py-0.5 rounded">
                            {tool.kind === 'cli' ? t('CLI') : t('Client')}
                          </span>
                          <span className="text-[9.5px] font-mono text-neutral-400 truncate" title={tool.path}>
                            {tool.path}
                          </span>
                        </div>
                        <div className="mt-3 flex items-center gap-3">
                          <button
                            type="button"
                            onClick={() => void handleConnect(tool.id)}
                            disabled={pendingId !== null}
                            className={`${BTN_PRIMARY} text-[10px] disabled:opacity-50`}
                          >
                            {pendingId === tool.id ? t('Connecting…') : t('Connect Tool')}
                          </button>
                          {!tool.registered && (
                            <button
                              type="button"
                              onClick={() => void handleAutoConfigure(tool.id)}
                              disabled={pendingId !== null}
                              className="text-[10px] font-semibold text-indigo-600 hover:text-indigo-800 transition-colors disabled:opacity-50 flex items-center gap-1"
                            >
                              {pendingId === tool.id ? (
                                <>
                                  <LegacyIcon name="progress_activity" className="animate-spin w-3 h-3 text-indigo-500" />
                                  Configuring…
                                </>
                              ) : (
                                <>
                                  <LegacyIcon name="bolt" className="w-3 h-3" />
                                  Auto Config
                                </>
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="text-left">
              <h3 className="text-xs font-bold text-neutral-900 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-neutral-200"></span>
                {t('Recommended to Install')}
              </h3>
              {notInstalledTools.length === 0 ? (
                <p className="text-xs text-neutral-400 italic">{t('All supported AI tools are installed.')}</p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {notInstalledTools.map((tool) => {
                    const isExpanded = expandedInstallId === tool.id;
                    const instruction = INSTALL_INSTRUCTIONS[tool.id] || {
                      cmd: `npm install -g ${tool.id.replace('-cli', '')}`,
                      desc: `Install ${tool.name} tool globally.`,
                    };

                    return (
                      <div key={tool.id} className="p-4 border border-dashed border-neutral-200 rounded-xl bg-neutral-50/50 flex flex-col gap-4">
                        <div className="flex items-start gap-4">
                          <AiToolIcon tool={tool} dimmed />
                          <div className="flex-1 min-w-0">
                            <h4 className="text-xs font-bold text-neutral-600">{tool.name}</h4>
                            <p className="text-[10px] text-neutral-400 mt-1 leading-relaxed">{tool.description}</p>
                            <div className="mt-1.5 flex items-center gap-1.5">
                              <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-neutral-400 bg-neutral-100 border border-neutral-200 px-1.5 py-0.5 rounded">
                                {tool.kind === 'cli' ? t('CLI') : t('Client')}
                              </span>
                              <span className="text-[9.5px] text-neutral-400 font-medium">
                                {t('Not Installed')}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => setExpandedInstallId(isExpanded ? null : tool.id)}
                              className="text-[10px] font-semibold text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-1"
                            >
                              <LegacyIcon name="settings" className="w-3 h-3" />
                              {isExpanded ? t('Hide Install Guide') : t('Install Guide')}
                            </button>
                            {instruction.url && (
                              <a
                                href={instruction.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[10px] font-semibold text-neutral-500 hover:text-neutral-700 transition-colors inline-flex items-center gap-0.5"
                              >
                                {t('Visit Website')}
                                <span className="text-[8px]">↗</span>
                              </a>
                            )}
                          </div>

                          {isExpanded && (
                            <div className="mt-2 p-3 bg-neutral-900 rounded-lg text-left text-[10px] font-mono text-neutral-200 relative group overflow-x-auto border border-neutral-800">
                              <div className="text-[9px] text-neutral-400 mb-1.5 leading-normal font-sans">
                                {instruction.desc}
                              </div>
                              <div className="flex items-center justify-between gap-4 mt-1 bg-neutral-950/80 p-2 rounded border border-neutral-800/60">
                                <code className="text-neutral-100 break-all select-all pr-2">
                                  {instruction.cmd}
                                </code>
                                <button
                                  type="button"
                                  onClick={() => {
                                    void navigator.clipboard.writeText(instruction.cmd);
                                    setCopiedId(tool.id);
                                    setTimeout(() => setCopiedId(null), 2000);
                                  }}
                                  className="text-neutral-400 hover:text-white transition-colors p-1 rounded hover:bg-neutral-800/80 flex-shrink-0"
                                  title={t('Copy command')}
                                >
                                  {copiedId === tool.id ? (
                                    <LegacyIcon name="check" className="w-3 h-3 text-green-400" />
                                  ) : (
                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" className="w-3.5 h-3.5">
                                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H5.4M9 13.5V5.25c0-.621.504-1.125 1.125-1.125h9.75c.621 0 1.125.504 1.125 1.125v12.25c0 .621-.504 1.125-1.125 1.125H10.125A1.125 1.125 0 0 1 9 17.25z" />
                                    </svg>
                                  )}
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </>
        )}
    </SettingsPageShell>
  );
}
