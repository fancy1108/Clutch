import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { DispatchPreviewPayload, PendingHandoffDraft } from '../../types';
import type { SessionRecord } from '../../services/runApi';
import type { ScannedSkill } from '../../services/skillsApi';
import type { FileTreeNode } from '../../services/workspaceApi';
import { PERMISSION_MODES, type PermissionMode } from '../../services/permissionApi';
import { clutchStore } from '../../services/clutchState';
import { resolveBrandLogoSrc } from '../../services/brandLogos';
import { DISPATCH_MENTION_OPTIONS } from '../../services/terminalOrchestraUtils';
import { useLanguage } from '../LanguageContext';
import { LegacyIcon } from '../ui/LegacyIcon';
import { DispatchConfirmCard } from './DispatchConfirmCard';

interface OrchestratorBarProps {
  sessionRunId: string;
  drafts: PendingHandoffDraft[];
  inputValue: string;
  setInputValue: (val: string) => void;
  permissionMode: PermissionMode;
  onPermissionModeChange: (mode: PermissionMode) => void;
  workspaceFiles?: FileTreeNode[];
  sessions?: SessionRecord[];
  skills?: ScannedSkill[];
  onFocusChange?: (focused: boolean) => void;
}

function flattenFileTree(nodes: FileTreeNode[], prefix = ''): string[] {
  const paths: string[] = [];
  for (const node of nodes) {
    const p = prefix ? `${prefix}/${node.name}` : node.name;
    paths.push(p);
    if (node.children) paths.push(...flattenFileTree(node.children, p));
  }
  return paths;
}

export const OrchestratorBar: React.FC<OrchestratorBarProps> = ({
  sessionRunId,
  drafts,
  inputValue,
  setInputValue,
  permissionMode,
  onPermissionModeChange,
  workspaceFiles = [],
  sessions = [],
  skills = [],
  onFocusChange,
}) => {
  const { t } = useLanguage();
  const [error, setError] = useState('');
  const [preview, setPreview] = useState<DispatchPreviewPayload | null>(null);
  const [activeChips, setActiveChips] = useState<string[]>([]);
  const [activeDraftId, setActiveDraftId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; draftText?: string } | null>(null);
  const [agentPickerOpen, setAgentPickerOpen] = useState(false);
  const [agentFilter, setAgentFilter] = useState('');
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [permissionMenuOpen, setPermissionMenuOpen] = useState(false);
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [sessionPickerOpen, setSessionPickerOpen] = useState(false);
  const [fileFilter, setFileFilter] = useState('');
  const [skillFilter, setSkillFilter] = useState('');
  const [sessionFilter, setSessionFilter] = useState('');
  const prevDraftCount = React.useRef(drafts.length);
  const containerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const currentPermission = PERMISSION_MODES.find((m) => m.id === permissionMode) ?? PERMISSION_MODES[0];
  const allFilePaths = flattenFileTree(workspaceFiles);
  const filteredFiles = allFilePaths.filter(
    (p) => !fileFilter || p.toLowerCase().includes(fileFilter.toLowerCase()),
  );
  const filteredAgents = DISPATCH_MENTION_OPTIONS.filter((option) =>
    option.mention.toLowerCase().includes(agentFilter.toLowerCase()),
  );
  const filteredSkills = skills.filter(
    (s) =>
      !skillFilter
      || s.label.toLowerCase().includes(skillFilter.toLowerCase())
      || s.key.toLowerCase().includes(skillFilter.toLowerCase()),
  );
  const filteredSessions = sessions.filter(
    (s) =>
      !sessionFilter
      || (s.title || '').toLowerCase().includes(sessionFilter.toLowerCase())
      || s.run_id.toLowerCase().includes(sessionFilter.toLowerCase()),
  );

  const closeAllPopovers = useCallback(() => {
    setAgentPickerOpen(false);
    setAttachMenuOpen(false);
    setPermissionMenuOpen(false);
    setFileBrowserOpen(false);
    setSkillPickerOpen(false);
    setSessionPickerOpen(false);
  }, []);

  useEffect(() => {
    const unsub = clutchStore.onDispatchError((message) => setError(message));
    return unsub;
  }, []);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<{ text: string }>).detail;
      if (detail?.text) setInputValue(detail.text);
    };
    window.addEventListener('orchestrator-fill-bar', handler);
    return () => window.removeEventListener('orchestrator-fill-bar', handler);
  }, [setInputValue]);

  useEffect(() => {
    if (drafts.length > prevDraftCount.current && drafts.length > 0) {
      const latest = drafts[drafts.length - 1];
      setToast({ message: latest.label, draftText: latest.text });
    }
    prevDraftCount.current = drafts.length;
  }, [drafts]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`;
  }, [inputValue]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        closeAllPopovers();
      }
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, [closeAllPopovers]);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const val = e.target.value;
      setInputValue(val);

      const lastAt = val.lastIndexOf('@');
      if (lastAt !== -1 && (lastAt === 0 || val[lastAt - 1] === ' ' || val[lastAt - 1] === '\n')) {
        const fragment = val.slice(lastAt + 1);
        if (!fragment.includes(' ')) {
          setAgentFilter(fragment);
          setAgentPickerOpen(true);
          setAttachMenuOpen(false);
          setPermissionMenuOpen(false);
          return;
        }
      }
      setAgentPickerOpen(false);
    },
    [setInputValue],
  );

  const insertDispatchAgent = useCallback(
    (mention: string) => {
      const lastAt = inputValue.lastIndexOf('@');
      const before = lastAt >= 0 ? inputValue.slice(0, lastAt) : inputValue;
      setInputValue(`${before}@${mention} `);
      setAgentPickerOpen(false);
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const insertProjectFile = useCallback(
    (path: string) => {
      const fileName = path.split('/').pop() || path;
      const lastAt = inputValue.lastIndexOf('@');
      const before = lastAt >= 0 ? inputValue.slice(0, lastAt) : inputValue;
      setInputValue(`${before}@${fileName} `);
      setFileBrowserOpen(false);
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const insertSkill = useCallback(
    (skill: ScannedSkill) => {
      const lastSlash = inputValue.lastIndexOf('/');
      const before = lastSlash >= 0 ? inputValue.slice(0, lastSlash) : inputValue;
      setInputValue(`${before}/skill:${skill.key} `);
      setSkillPickerOpen(false);
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const insertSession = useCallback(
    (session: SessionRecord) => {
      const lastHash = inputValue.lastIndexOf('#');
      const before = lastHash >= 0 ? inputValue.slice(0, lastHash) : inputValue;
      const label = session.title || session.run_id;
      setInputValue(`${before}#${label} `);
      setSessionPickerOpen(false);
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const handleLocalFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!e.target.files) return;
      let next = inputValue;
      for (const file of Array.from(e.target.files)) {
        next = `[file: ${file.name}]\n${next}`;
      }
      setInputValue(next);
      e.target.value = '';
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const handleSend = useCallback(async () => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;
    setError('');
    const result = await clutchStore.previewDispatch(trimmed);
    if (!result.ok) {
      setError(result.error);
      setPreview(null);
      return;
    }
    setPreview(result.preview);
    setActiveChips(
      (result.preview.chips ?? []).filter((c) => c.on).map((c) => c.source_name),
    );
  }, [inputValue]);

  const handleConfirm = useCallback(async () => {
    if (!preview) return;
    setError('');
    setPreview(null);
    await clutchStore.confirmDispatch(inputValue.trim(), activeChips);
    setInputValue('');
    setActiveDraftId(null);
  }, [preview, inputValue, activeChips, setInputValue]);

  const toggleChip = (sourceName: string) => {
    setActiveChips((prev) =>
      prev.includes(sourceName) ? prev.filter((s) => s !== sourceName) : [...prev, sourceName],
    );
  };

  const selectDraft = (draft: PendingHandoffDraft) => {
    setActiveDraftId(draft.id);
    setInputValue(draft.text);
  };

  const canSend = inputValue.trim().length > 0;

  return (
    <div
      ref={containerRef}
      data-testid="orchestrator-bar"
      className="w-full max-w-2xl bg-white border border-outline-variant shadow-xl rounded-xl transition-all focus-within:ring-2 focus-within:ring-primary/10 relative"
    >
      <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleLocalFileChange} />

      {toast ? (
        <div className="flex items-center gap-2 rounded-t-xl border-b border-outline-variant/40 bg-surface-container-low px-3 py-2 text-xs">
          <span className="flex-1 text-on-surface">{toast.message}</span>
          {toast.draftText ? (
            <button
              type="button"
              className="text-[10px] font-semibold px-2 py-1 rounded-lg border border-outline-variant/40 hover:bg-surface-container-high"
              onClick={() => {
                setInputValue(toast.draftText ?? '');
                setToast(null);
              }}
            >
              {t('Fill draft')}
            </button>
          ) : null}
          <button
            type="button"
            className="text-[10px] font-semibold px-2 py-1 rounded-lg border border-outline-variant/40 hover:bg-surface-container-high"
            onClick={() => setToast(null)}
          >
            {t('Dismiss toast')}
          </button>
        </div>
      ) : null}

      {error ? (
        <div
          data-testid="orchestrator-dock-error"
          className="mx-3 mt-2 rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-[11px] text-error"
        >
          {error}
        </div>
      ) : null}

      {drafts.length > 0 ? (
        <div className="flex flex-wrap gap-1.5 px-3 pt-2 pb-1">
          {drafts.map((draft) => (
            <button
              key={draft.id}
              type="button"
              onClick={() => selectDraft(draft)}
              className={`text-[10px] font-semibold px-2 py-1 rounded-lg border ${
                activeDraftId === draft.id
                  ? 'border-amber-500 bg-amber-50 text-amber-900'
                  : 'border-outline-variant/40 bg-amber-50/60 text-amber-800'
              }`}
            >
              {draft.label}
            </button>
          ))}
        </div>
      ) : null}

      <div className="relative flex items-end gap-1.5 px-2 py-1.5">
        {preview ? (
          <DispatchConfirmCard
            preview={preview}
            activeChips={activeChips}
            onToggleChip={toggleChip}
            onCancel={() => setPreview(null)}
            onConfirm={() => void handleConfirm()}
          />
        ) : null}

        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => {
              setAttachMenuOpen((v) => !v);
              setPermissionMenuOpen(false);
            }}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-on-surface-variant/60 hover:text-on-surface hover:bg-surface-container transition-colors"
            title={t('Attach')}
          >
            <LegacyIcon name="add" className="text-[19px]" />
          </button>

          {attachMenuOpen ? (
            <div className="absolute bottom-full left-0 mb-2 w-52 bg-white border border-outline-variant rounded-xl shadow-xl py-1.5 z-50 animate-in fade-in slide-in-from-bottom-1 duration-150">
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  fileInputRef.current?.click();
                }}
              >
                <LegacyIcon name="attach_file" className="text-[17px] text-on-surface-variant" />
                Add attachment
              </button>
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  setFileBrowserOpen(true);
                  setFileFilter('');
                }}
              >
                <LegacyIcon name="alternate_email" className="text-[17px] text-on-surface-variant" />
                Insert @ mention
              </button>
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  setSessionPickerOpen(true);
                }}
              >
                <LegacyIcon name="chat_bubble" className="text-[17px] text-on-surface-variant" />
                Insert # session
              </button>
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  setSkillPickerOpen(true);
                  setSkillFilter('');
                }}
              >
                <LegacyIcon name="terminal" className="text-[17px] text-on-surface-variant" />
                Insert / command
              </button>
            </div>
          ) : null}
        </div>

        <textarea
          ref={textareaRef}
          data-testid="orchestrator-input"
          rows={1}
          value={inputValue}
          onChange={handleInputChange}
          onFocus={() => onFocusChange?.(true)}
          onBlur={() => onFocusChange?.(false)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              closeAllPopovers();
              return;
            }
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
            if (e.key === 'ArrowUp' && e.metaKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
          placeholder={t('Orchestrator input placeholder')}
          className="w-full border-none focus:ring-0 text-[13px] text-on-surface bg-transparent py-1.5 resize-none min-h-[36px] max-h-[140px] placeholder:text-on-surface-variant/60 outline-none leading-relaxed"
        />

        <div className="flex items-center gap-1 flex-shrink-0">
          <div className="relative">
            <button
              type="button"
              title={`Permission: ${currentPermission.label}`}
              onClick={() => {
                setPermissionMenuOpen((v) => !v);
                setAttachMenuOpen(false);
              }}
              className={`w-8 h-8 flex items-center justify-center rounded-lg transition-colors ${
                permissionMode === 'full'
                  ? 'text-amber-500 hover:bg-amber-50'
                  : permissionMode === 'plan'
                    ? 'text-blue-500 hover:bg-blue-50'
                    : permissionMode === 'auto_edit'
                      ? 'text-emerald-500 hover:bg-emerald-50'
                      : 'text-on-surface-variant/60 hover:text-on-surface hover:bg-surface-container'
              }`}
            >
              <LegacyIcon name={currentPermission.icon} className="text-[18px]" />
            </button>

            {permissionMenuOpen ? (
              <div className="absolute bottom-full right-0 mb-2 w-60 bg-white border border-outline-variant rounded-xl shadow-xl py-1.5 z-50 animate-in fade-in slide-in-from-bottom-1 duration-150">
                {PERMISSION_MODES.map((mode) => (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => {
                      onPermissionModeChange(mode.id);
                      setPermissionMenuOpen(false);
                    }}
                    className="w-full flex items-start gap-3 px-3 py-2.5 hover:bg-surface-container-low transition-colors text-left group"
                  >
                    <LegacyIcon
                      name={mode.icon}
                      className={`text-[18px] mt-0.5 flex-shrink-0 ${
                        mode.id === permissionMode
                          ? mode.id === 'full'
                            ? 'text-amber-500'
                            : mode.id === 'plan'
                              ? 'text-blue-500'
                              : mode.id === 'auto_edit'
                                ? 'text-emerald-500'
                                : 'text-on-surface-variant'
                          : 'text-on-surface-variant/50'
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-[12px] font-semibold text-on-surface">{mode.label}</span>
                        {mode.id === permissionMode ? (
                          <LegacyIcon name="check" className="text-[14px] text-primary" />
                        ) : null}
                      </div>
                      <span className="text-[10.5px] text-on-surface-variant/70">{mode.description}</span>
                    </div>
                  </button>
                ))}
                <div className="border-t border-outline-variant/60 my-1 mx-3" />
                <div className="px-3 py-1.5 text-[9.5px] leading-normal text-on-surface-variant/60">
                  {t('Note: These settings only apply to the built-in Clutch Agent and MCP tools, and do not affect CLI Agents (such as Claude Code).')}
                </div>
              </div>
            ) : null}
          </div>

          <button
            type="button"
            data-testid="orchestrator-send-btn"
            title={t('Send')}
            disabled={!canSend}
            onClick={() => void handleSend()}
            className={`w-8 h-8 flex items-center justify-center rounded-full transition-all ${
              canSend
                ? 'bg-primary text-white hover:opacity-90'
                : 'bg-surface-container text-on-surface-variant/40 cursor-not-allowed'
            }`}
          >
            <LegacyIcon name="arrow_upward" className="text-[17px]" />
          </button>
        </div>
      </div>

      {agentPickerOpen ? (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="alternate_email" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">{t('Dispatch agents')}</span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredAgents.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">{t('No matching agents')}</p>
            ) : (
              filteredAgents.map((option) => {
                const logo = resolveBrandLogoSrc({ agentType: option.agentType });
                return (
                  <button
                    key={option.agentType}
                    type="button"
                    onClick={() => insertDispatchAgent(option.mention)}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                  >
                    {logo ? (
                      <img src={logo} alt="" className="w-5 h-5 rounded object-contain shrink-0" />
                    ) : (
                      <span className="w-5 h-5 rounded bg-surface-container-low shrink-0" />
                    )}
                    <span className="text-[12px] font-semibold text-on-surface">{option.mention}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      ) : null}

      {skillPickerOpen ? (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="terminal" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">{t('Skills / Commands')}</span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredSkills.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">
                {skills.length === 0 ? t('No skills loaded') : t('No matches')}
              </p>
            ) : (
              filteredSkills.map((skill) => (
                <button
                  key={skill.key}
                  type="button"
                  onClick={() => insertSkill(skill)}
                  className="w-full flex flex-col px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                >
                  <span className="text-[12px] font-semibold text-on-surface">{skill.label}</span>
                  {skill.desc ? (
                    <span className="text-[10.5px] text-on-surface-variant/60 truncate">{skill.desc}</span>
                  ) : null}
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}

      {sessionPickerOpen ? (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="chat_bubble" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">{t('Sessions')}</span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredSessions.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">{t('No sessions yet')}</p>
            ) : (
              filteredSessions.slice(0, 12).map((session) => (
                <button
                  key={session.run_id}
                  type="button"
                  onClick={() => insertSession(session)}
                  className="w-full flex flex-col px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                >
                  <span className="text-[12px] font-semibold text-on-surface truncate">
                    {session.title || session.run_id}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}

      {fileBrowserOpen ? (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2 pb-1">
              <LegacyIcon name="folder_open" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">{t('Project Files')}</span>
            </div>
            <input
              type="text"
              value={fileFilter}
              onChange={(e) => setFileFilter(e.target.value)}
              placeholder={t('Filter files...')}
              className="w-full text-[11px] px-2 py-1.5 bg-surface-container rounded-lg border-none outline-none text-on-surface placeholder:text-on-surface-variant/50"
              autoFocus
            />
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredFiles.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">
                {allFilePaths.length === 0 ? t('No workspace files loaded') : t('No matches')}
              </p>
            ) : (
              filteredFiles.slice(0, 30).map((path) => (
                <button
                  key={path}
                  type="button"
                  onClick={() => insertProjectFile(path)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-surface-container-low transition-colors"
                >
                  <LegacyIcon
                    name={path.endsWith('/') ? 'folder' : 'description'}
                    className="text-[14px] text-on-surface-variant flex-shrink-0"
                  />
                  <span className="text-[11px] text-on-surface truncate" title={path}>{path}</span>
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}

      <span className="sr-only">{sessionRunId}</span>
    </div>
  );
};
