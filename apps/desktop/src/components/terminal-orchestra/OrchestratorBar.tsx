import React, { useCallback, useEffect, useRef, useState } from 'react';
import type { SessionRecord } from '../../services/runApi';
import type { ScannedSkill } from '../../services/skillsApi';
import type { FileTreeNode } from '../../services/workspaceApi';
import {
  normalizePermissionMode,
  PERMISSION_MODES,
  type PermissionMode,
} from '../../services/permissionApi';
import { clutchStore } from '../../services/clutchState';
import {
  buildOptimisticDispatchEntry,
  collectHandoffLaneTranscripts,
  findLaneForDispatchSource,
  normalizeOrchestratorDispatchText,
  parseInputAgentMention,
  resolveDispatchTargetAgent,
} from '../../services/terminalOrchestraUtils';
import { uploadWorkspaceAttachment } from '../../services/workspaceApi';
import { useLanguage } from '../LanguageContext';
import { LegacyIcon } from '../ui/LegacyIcon';

type ImageChip = { id: string; name: string; dataUrl: string };

interface OrchestratorBarProps {
  sessionRunId: string;
  inputValue: string;
  setInputValue: (val: string) => void;
  permissionMode: PermissionMode;
  onPermissionModeChange: (mode: PermissionMode) => void;
  workspaceFiles?: FileTreeNode[];
  sessions?: SessionRecord[];
  skills?: ScannedSkill[];
  onFocusChange?: (focused: boolean) => void;
  mentionableAgents?: Array<{ id: string; name: string; logo?: string; dispatchTarget: string; agentType?: string }>;
  selectedMentionAgentId?: string | null;
  onMentionAgentChange?: (agentId: string | null) => void;
  readOnly?: boolean;
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
  inputValue,
  setInputValue,
  permissionMode,
  onPermissionModeChange,
  workspaceFiles = [],
  sessions = [],
  skills = [],
  onFocusChange,
  mentionableAgents = [],
  selectedMentionAgentId = null,
  onMentionAgentChange,
  readOnly = false,
}) => {
  const { t } = useLanguage();
  const [error, setError] = useState('');
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
  const [imageChips, setImageChips] = useState<ImageChip[]>([]);
  const [sending, setSending] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const sendingLockRef = useRef(false);

  const resolvedPermissionMode = normalizePermissionMode(permissionMode);
  const currentPermission =
    PERMISSION_MODES.find((m) => m.id === resolvedPermissionMode) ?? PERMISSION_MODES[0];
  const allFilePaths = flattenFileTree(workspaceFiles);
  const filteredFiles = allFilePaths.filter(
    (p) => !fileFilter || p.toLowerCase().includes(fileFilter.toLowerCase()),
  );
  const filteredAgents = mentionableAgents.filter((agent) =>
    agent.name.toLowerCase().includes(agentFilter.toLowerCase()),
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

  useEffect(() => {
    if (!onMentionAgentChange) return;
    const hit = parseInputAgentMention(inputValue, mentionableAgents);
    onMentionAgentChange(hit?.agentId ?? null);
  }, [inputValue, mentionableAgents, onMentionAgentChange]);

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

  const insertMentionAgent = useCallback(
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
        if (file.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = () => {
            setImageChips((prev) => [
              ...prev,
              {
                id: `${Date.now()}-${file.name}`,
                name: file.name,
                dataUrl: reader.result as string,
              },
            ]);
          };
          reader.readAsDataURL(file);
          continue;
        }
        next = `[file: ${file.name}]\n${next}`;
      }
      setInputValue(next);
      e.target.value = '';
      textareaRef.current?.focus();
    },
    [inputValue, setInputValue],
  );

  const addImageFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = () => {
      setImageChips((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          name: file.name || 'clipboard.png',
          dataUrl: reader.result as string,
        },
      ]);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleImageInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!e.target.files) return;
      for (const file of Array.from(e.target.files)) {
        addImageFile(file);
      }
      e.target.value = '';
      textareaRef.current?.focus();
    },
    [addImageFile],
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      if (readOnly || sending) return;
      const { files } = e.clipboardData;
      if (!files || files.length === 0) return;
      let hasImage = false;
      for (const file of Array.from(files)) {
        if (file.type.startsWith('image/')) {
          e.preventDefault();
          addImageFile(file);
          hasImage = true;
        }
      }
      if (hasImage) return;
    },
    [addImageFile, readOnly, sending],
  );

  const handleSend = useCallback(async () => {
    if (sendingLockRef.current || readOnly) return;
    const trimmed = inputValue.trim();
    if (!trimmed && imageChips.length === 0) return;
    sendingLockRef.current = true;
    setSending(true);
    setError('');
    try {
      let composed = trimmed;
      if (imageChips.length > 0) {
        const parts: string[] = [];
        for (const chip of imageChips) {
          const uploaded = await uploadWorkspaceAttachment(chip.dataUrl, { analyze: false });
          parts.push(`[file: ${uploaded.path}]`);
          parts.push(`@${uploaded.path}`);
        }
        composed = `${parts.join('\n')}\n${trimmed}`.trim();
      }
      if (!composed) return;
      const dispatchText = normalizeOrchestratorDispatchText(composed, mentionableAgents);
      const result = await clutchStore.previewDispatch(dispatchText);
      if (!result.ok) {
        setError(result.error);
        return;
      }
      const preview = result.preview;
      const chips = (preview.chips ?? []).filter((c) => c.on).map((c) => c.source_name);
      const targetAgent = resolveDispatchTargetAgent(
        composed,
        preview.target,
        mentionableAgents,
        selectedMentionAgentId,
      );
      const snapshot = clutchStore.getSnapshot();
      const isHandoff = preview.dispatch_mode === 'handoff';
      const laneTranscripts = isHandoff
        ? collectHandoffLaneTranscripts(
            chips.length > 0 ? chips : preview.sources,
            snapshot.pty_lanes ?? [],
            (laneId) => clutchStore.getLaneTranscript(laneId),
            preview.target,
          )
        : [];
      const targetLabel = targetAgent?.name?.trim() || preview.target;
      clutchStore.optimisticDispatchLogAppend(
        buildOptimisticDispatchEntry({
          prompt: dispatchText,
          preview,
          activeSources: chips,
          targetLabel,
        }),
      );
      if (!isHandoff) {
        const sourcesToCollapse = chips.length > 0 ? chips : preview.sources;
        for (const src of sourcesToCollapse) {
          const sourceLane = findLaneForDispatchSource(snapshot.pty_lanes ?? [], src);
          if (sourceLane) {
            void clutchStore.collapseLane(sourceLane.lane_id, true);
          }
        }
      }
      await clutchStore.confirmDispatch(dispatchText, chips, {
        id: targetAgent?.agentId,
        name: targetAgent?.name,
      }, laneTranscripts);
      if (targetAgent) {
        onMentionAgentChange?.(targetAgent.agentId);
      }
      setInputValue('');
      setImageChips([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      sendingLockRef.current = false;
      setSending(false);
    }
  }, [
    imageChips,
    inputValue,
    mentionableAgents,
    onMentionAgentChange,
    readOnly,
    selectedMentionAgentId,
    setInputValue,
  ]);

  const canSend = !readOnly && !sending && (inputValue.trim().length > 0 || imageChips.length > 0);

  return (
    <div
      ref={containerRef}
      data-testid="orchestrator-bar"
      className={`relative w-full bg-white border border-outline-variant shadow-xl rounded-xl transition-all ${
        readOnly ? 'opacity-70' : 'focus-within:ring-2 focus-within:ring-primary/10'
      }`}
    >
      <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleLocalFileChange} />
      <input
        ref={imageInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={handleImageInputChange}
      />

      {error ? (
        <div
          data-testid="orchestrator-dock-error"
          className="mx-3 mt-2 rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-[11px] text-error"
        >
          {error}
        </div>
      ) : null}

      {imageChips.length > 0 ? (
        <div className="flex flex-wrap gap-2 px-3 pt-2 pb-1" data-testid="orchestrator-image-chips">
          {imageChips.map((chip) => (
            <div
              key={chip.id}
              className="relative w-14 h-14 rounded-lg border border-outline-variant/50 overflow-hidden bg-surface-container-low"
            >
              <img src={chip.dataUrl} alt={chip.name} className="w-full h-full object-cover" />
              {sending ? (
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                  <LegacyIcon name="progress_activity" className="text-[18px] text-white animate-spin" />
                </div>
              ) : (
                <button
                  type="button"
                  className="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/55 text-white flex items-center justify-center"
                  onClick={() => setImageChips((prev) => prev.filter((c) => c.id !== chip.id))}
                  title={t('Remove')}
                >
                  <LegacyIcon name="close" className="text-[12px]" />
                </button>
              )}
            </div>
          ))}
        </div>
      ) : null}

      <div className="relative flex items-end gap-1.5 px-2 py-1.5">
        {!readOnly ? (
        <div className="relative flex-shrink-0">
          <button
            type="button"
            disabled={sending}
            onClick={() => {
              setAttachMenuOpen((v) => !v);
              setPermissionMenuOpen(false);
            }}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-on-surface-variant/60 hover:text-on-surface hover:bg-surface-container transition-colors disabled:opacity-50"
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
                  imageInputRef.current?.click();
                }}
              >
                <LegacyIcon name="image" className="text-[17px] text-on-surface-variant" />
                Image
              </button>
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
                <LegacyIcon name="history" className="text-[17px] text-on-surface-variant" />
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
                <LegacyIcon name="sparkles" className="text-[17px] text-on-surface-variant" />
                Insert / command
              </button>
            </div>
          ) : null}
        </div>
        ) : null}

        <textarea
          ref={textareaRef}
          data-testid="orchestrator-input"
          rows={1}
          value={inputValue}
          onChange={handleInputChange}
          onPaste={handlePaste}
          onFocus={() => !readOnly && onFocusChange?.(true)}
          onBlur={() => onFocusChange?.(false)}
          disabled={readOnly || sending}
          readOnly={readOnly}
          onKeyDown={(e) => {
            if (readOnly || sending) return;
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
          placeholder={readOnly ? t('Historical session is read-only') : t('Orchestrator input placeholder')}
          className={`w-full border-none focus:ring-0 text-[13px] text-on-surface bg-transparent py-1.5 resize-none min-h-[36px] max-h-[140px] placeholder:text-on-surface-variant/60 outline-none leading-relaxed ${
            readOnly || sending ? 'cursor-not-allowed opacity-70' : ''
          }`}
        />

        <div className="flex items-center gap-1 flex-shrink-0">
          {!readOnly ? (
          <div className="relative">
            <button
              type="button"
              title={`Permission: ${currentPermission.label}`}
              aria-label={`Permission: ${currentPermission.label}`}
              aria-expanded={permissionMenuOpen}
              onClick={() => {
                setPermissionMenuOpen((v) => !v);
                setAttachMenuOpen(false);
              }}
              className={`inline-flex h-7 items-center gap-1 rounded-full pl-2 pr-1.5 text-[12px] font-medium leading-none transition-colors ${
                permissionMenuOpen
                  ? 'bg-surface-container-high text-on-surface'
                  : 'bg-surface-container text-on-surface/90 hover:bg-surface-container-high hover:text-on-surface'
              }`}
            >
              <LegacyIcon name={currentPermission.icon} className="text-[15px] opacity-90" />
              <span>{currentPermission.label}</span>
              <LegacyIcon
                name="expand_more"
                className={`text-[14px] opacity-45 transition-transform duration-150 ${
                  permissionMenuOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {permissionMenuOpen ? (
              <div className="absolute bottom-full right-0 mb-2 w-56 overflow-hidden rounded-xl border border-outline-variant/50 bg-white py-1 shadow-[0_8px_28px_rgba(15,23,42,0.12)] z-50 animate-in fade-in slide-in-from-bottom-1 duration-150">
                {PERMISSION_MODES.map((mode) => {
                  const selected = mode.id === resolvedPermissionMode;
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => {
                        onPermissionModeChange(mode.id);
                        setPermissionMenuOpen(false);
                      }}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors ${
                        selected
                          ? 'bg-surface-container/90'
                          : 'hover:bg-surface-container-low'
                      }`}
                    >
                      <LegacyIcon
                        name={mode.icon}
                        className={`text-[16px] flex-shrink-0 ${
                          selected ? 'text-on-surface' : 'text-on-surface-variant/55'
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={`text-[12.5px] ${
                              selected ? 'font-semibold text-on-surface' : 'font-medium text-on-surface'
                            }`}
                          >
                            {mode.label}
                          </span>
                          {selected ? (
                            <LegacyIcon name="check" className="text-[14px] text-on-surface" />
                          ) : null}
                        </div>
                        <span className="block text-[10px] text-on-surface-variant/60 leading-snug mt-0.5">
                          {mode.description}
                        </span>
                      </div>
                    </button>
                  );
                })}
                <div className="border-t border-outline-variant/40 my-1 mx-2" />
                <div className="px-3 py-1.5 text-[9.5px] leading-normal text-on-surface-variant/50">
                  {t('Note: These settings only apply to the built-in Clutch Agent and MCP tools, and do not affect CLI Agents (such as Claude Code).')}
                </div>
              </div>
            ) : null}
          </div>
          ) : null}

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
            <LegacyIcon
              name={sending ? 'progress_activity' : 'arrow_upward'}
              className={`text-[17px] ${sending ? 'animate-spin' : ''}`}
            />
          </button>
        </div>
      </div>

      {agentPickerOpen ? (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="alternate_email" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">{t('AI Agents')}</span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredAgents.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">{t('No matching agents')}</p>
            ) : (
              filteredAgents.map((agent) => (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => insertMentionAgent(agent.name)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-surface-container-low transition-colors"
                >
                  {agent.logo ? (
                    <img src={agent.logo} alt="" className="w-5 h-5 rounded object-contain shrink-0" />
                  ) : (
                    <span className="w-5 h-5 rounded bg-surface-container-low shrink-0" />
                  )}
                  <span className="flex-1 min-w-0 flex items-center justify-between gap-2">
                    <span className="text-[12px] font-semibold text-on-surface truncate">@{agent.name}</span>
                    {agent.id === selectedMentionAgentId ? (
                      <LegacyIcon name="check" className="text-[14px] text-primary shrink-0" />
                    ) : null}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}

      {skillPickerOpen ? (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="sparkles" className="text-[15px] text-on-surface-variant" />
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
              <LegacyIcon name="history" className="text-[15px] text-on-surface-variant" />
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
