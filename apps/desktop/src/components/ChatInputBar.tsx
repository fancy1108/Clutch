/**
 * ChatInputBar — Rich chat input with:
 *  - Image paste (chip preview with thumbnail)
 *  - File/folder drag-and-drop from right panel (chip with icon)
 *  - + menu: local attach / project file / skill command / session
 *  - Permission mode selector (4 modes, backend-persisted)
 *  - / command → skill picker popover
 *  - # → session picker popover
 */
import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useLanguage } from './LanguageContext';
import type { SessionRecord } from '../services/runApi';
import type { ScannedSkill } from '../services/skillsApi';
import type { FileTreeNode } from '../services/workspaceApi';
import { PERMISSION_MODES, type PermissionMode } from '../services/permissionApi';
import { LegacyIcon } from './ui/LegacyIcon';
import { BTN_ICON_SM } from './ui/buttonStyles';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface Attachment {
  id: string;
  kind: 'image' | 'file' | 'folder';
  name: string;
  path?: string;         // for file/folder
  dataUrl?: string;      // for image preview
  mimeType?: string;
}

interface ChatInputBarProps {
  inputValue: string;
  setInputValue: (val: string) => void;
  onSendMessage: (text: string, attachments: Attachment[]) => void;
  isRunning: boolean;
  isPlainLlmChat: boolean;
  onStopRun?: () => void;
  selectedWorkflowId?: string | null;
  selectedWorkflowName?: string;
  onClearSelectedWorkflow?: () => void;
  isMultiAgent?: boolean;
  workspaceFiles?: FileTreeNode[];
  sessions?: SessionRecord[];
  skills?: ScannedSkill[];
  permissionMode: PermissionMode;
  onPermissionModeChange: (mode: PermissionMode) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function uid() {
  return Math.random().toString(36).slice(2, 9);
}

function fileIcon(kind: Attachment['kind']): string {
  if (kind === 'image') return 'image';
  if (kind === 'folder') return 'folder';
  return 'description';
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

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function AttachmentChip({
  att,
  onRemove,
}: {
  att: Attachment;
  onRemove: (id: string) => void;
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5 pl-1.5 pr-1 py-0.5 bg-surface-container border border-outline-variant/40 rounded-lg text-[11px] font-medium text-on-surface max-w-[160px] flex-shrink-0"
    >
      {att.kind === 'image' && att.dataUrl ? (
        <img
          src={att.dataUrl}
          alt={att.name}
          className="w-[22px] h-[22px] rounded object-cover flex-shrink-0 border border-outline-variant/30"
        />
      ) : (
        <LegacyIcon name={fileIcon(att.kind)} className="text-[15px] text-on-surface-variant flex-shrink-0" />
      )}
      <span className="truncate" title={att.name}>{att.name}</span>
      <button
        type="button"
        onClick={() => onRemove(att.id)}
        className={`${BTN_ICON_SM} ml-0.5 flex-shrink-0`}
        aria-label={`Remove ${att.name}`}
      >
        <LegacyIcon name="close" className="text-[13px]" />
      </button>
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

export const ChatInputBar: React.FC<ChatInputBarProps> = ({
  inputValue,
  setInputValue,
  onSendMessage,
  isRunning,
  isPlainLlmChat,
  onStopRun,
  selectedWorkflowId,
  selectedWorkflowName,
  onClearSelectedWorkflow,
  isMultiAgent,
  workspaceFiles = [],
  sessions = [],
  skills = [],
  permissionMode,
  onPermissionModeChange,
}) => {
  const { t } = useLanguage();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Menus
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [permissionMenuOpen, setPermissionMenuOpen] = useState(false);

  // Popovers
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [sessionPickerOpen, setSessionPickerOpen] = useState(false);
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);

  const [skillFilter, setSkillFilter] = useState('');
  const [sessionFilter, setSessionFilter] = useState('');
  const [fileFilter, setFileFilter] = useState('');

  // Close all menus on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setAttachMenuOpen(false);
        setPermissionMenuOpen(false);
        setSkillPickerOpen(false);
        setSessionPickerOpen(false);
        setFileBrowserOpen(false);
      }
    };
    window.addEventListener('mousedown', handler);
    return () => window.removeEventListener('mousedown', handler);
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 140)}px`;
  }, [inputValue]);

  // ── Attachment helpers ──────────────────────────────────────────────────────

  const addImageFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      setAttachments((prev) => [
        ...prev,
        {
          id: uid(),
          kind: 'image',
          name: file.name,
          dataUrl: reader.result as string,
          mimeType: file.type,
        },
      ]);
    };
    reader.readAsDataURL(file);
  }, []);

  const addFilePath = useCallback((path: string, isFolder = false) => {
    const name = path.split('/').pop() || path;
    setAttachments((prev) => [
      ...prev,
      { id: uid(), kind: isFolder ? 'folder' : 'file', name, path },
    ]);
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  // ── Paste handler ───────────────────────────────────────────────────────────

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
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
      if (hasImage) return; // let text paste fall through normally
    },
    [addImageFile],
  );

  // ── Drag & Drop handler ─────────────────────────────────────────────────────

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    if (!containerRef.current?.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      // Files dropped from OS
      if (e.dataTransfer.files.length > 0) {
        for (const file of Array.from(e.dataTransfer.files)) {
          if (file.type.startsWith('image/')) {
            addImageFile(file);
          } else {
            addFilePath(file.name);
          }
        }
        return;
      }

      // Path dropped from right panel file tree (text/plain = path string)
      const textData = e.dataTransfer.getData('text/plain');
      if (textData) {
        const isFolder = !textData.includes('.');
        addFilePath(textData, isFolder);
      }
    },
    [addImageFile, addFilePath],
  );

  // ── Local file picker ───────────────────────────────────────────────────────

  const handleLocalFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!e.target.files) return;
      for (const file of Array.from(e.target.files)) {
        if (file.type.startsWith('image/')) {
          addImageFile(file);
        } else {
          addFilePath(file.name);
        }
      }
      e.target.value = '';
    },
    [addImageFile, addFilePath],
  );

  // ── Keyboard handler ────────────────────────────────────────────────────────

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Escape') {
        setSkillPickerOpen(false);
        setSessionPickerOpen(false);
        setFileBrowserOpen(false);
        return;
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (isRunning && isPlainLlmChat) return;
        if (inputValue.trim() || attachments.length > 0) {
          handleSend();
        }
      }
    },
    [inputValue, attachments, isRunning, isPlainLlmChat],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const val = e.target.value;
      setInputValue(val);

      // Detect slash trigger for skills
      const lastSlash = val.lastIndexOf('/');
      if (lastSlash !== -1 && (lastSlash === 0 || val[lastSlash - 1] === ' ' || val[lastSlash - 1] === '\n')) {
        const fragment = val.slice(lastSlash + 1);
        if (!fragment.includes(' ')) {
          setSkillFilter(fragment);
          setSkillPickerOpen(true);
          setSessionPickerOpen(false);
          return;
        }
      }
      setSkillPickerOpen(false);

      // Detect hash trigger for sessions
      const lastHash = val.lastIndexOf('#');
      if (lastHash !== -1 && (lastHash === 0 || val[lastHash - 1] === ' ' || val[lastHash - 1] === '\n')) {
        const fragment = val.slice(lastHash + 1);
        if (!fragment.includes(' ')) {
          setSessionFilter(fragment);
          setSessionPickerOpen(true);
          return;
        }
      }
      setSessionPickerOpen(false);
    },
    [setInputValue],
  );

  // ── Send ────────────────────────────────────────────────────────────────────

  const handleSend = useCallback(() => {
    if (!inputValue.trim() && attachments.length === 0) return;
    onSendMessage(inputValue, attachments);
    setAttachments([]);
    setInputValue('');
  }, [inputValue, attachments, onSendMessage, setInputValue]);

  // ── Skill / Session insert ──────────────────────────────────────────────────

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

  const insertProjectFile = useCallback(
    (path: string) => {
      addFilePath(path);
      setFileBrowserOpen(false);
      textareaRef.current?.focus();
    },
    [addFilePath],
  );

  // ── Derived ─────────────────────────────────────────────────────────────────

  const filteredSkills = skills.filter(
    (s) =>
      !skillFilter ||
      s.label.toLowerCase().includes(skillFilter.toLowerCase()) ||
      s.key.toLowerCase().includes(skillFilter.toLowerCase()),
  );
  const filteredSessions = sessions.filter(
    (s) =>
      !sessionFilter ||
      (s.title || '').toLowerCase().includes(sessionFilter.toLowerCase()) ||
      s.run_id.toLowerCase().includes(sessionFilter.toLowerCase()),
  );
  const allFilePaths = flattenFileTree(workspaceFiles);
  const filteredFiles = allFilePaths.filter(
    (p) => !fileFilter || p.toLowerCase().includes(fileFilter.toLowerCase()),
  );

  const canSend = (inputValue.trim().length > 0 || attachments.length > 0) && !(isRunning && isPlainLlmChat);
  const currentPermission = PERMISSION_MODES.find((m) => m.id === permissionMode) ?? PERMISSION_MODES[0];

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div
      ref={containerRef}
      className={`w-full max-w-2xl bg-white border shadow-xl rounded-xl transition-all ${
        isDragging
          ? 'border-primary/60 ring-2 ring-primary/20'
          : 'border-outline-variant focus-within:ring-2 focus-within:ring-primary/10'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Hidden native file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleLocalFileChange}
      />

      {/* Workflow chip — Multi-Agent only */}
      {isMultiAgent && selectedWorkflowId ? (
        <div className="flex flex-wrap gap-1.5 px-3 pt-2 pb-1">
          <span className="inline-flex items-center gap-1.5 pl-1.5 pr-1 py-0.5 text-[11px] font-bold text-primary bg-primary/5 border border-primary/20 rounded-lg max-w-[220px]">
            <LegacyIcon name="account_tree" className="text-[14px] flex-shrink-0" />
            <span className="truncate" title={selectedWorkflowName || selectedWorkflowId}>
              {selectedWorkflowName || selectedWorkflowId}
            </span>
            <button
              type="button"
              onClick={onClearSelectedWorkflow}
              className={`${BTN_ICON_SM} ml-0.5 text-primary/60 hover:text-primary flex-shrink-0`}
              aria-label={t('Remove workflow')}
            >
              <LegacyIcon name="close" className="text-[13px]" />
            </button>
          </span>
        </div>
      ) : null}

      {/* Attachment chips */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-3 pt-2 pb-0.5">
          {attachments.map((att) => (
            <AttachmentChip key={att.id} att={att} onRemove={removeAttachment} />
          ))}
        </div>
      )}

      {/* Drop overlay hint */}
      {isDragging && (
        <div className="px-3 pt-2 pb-0">
          <div className="flex items-center gap-2 py-2 px-3 bg-primary/5 border border-primary/20 rounded-lg">
            <LegacyIcon name="upload_file" className="text-primary text-[18px]" />
            <span className="text-xs text-primary font-medium">Drop to attach</span>
          </div>
        </div>
      )}

      {/* Text area row */}
      <div className="flex items-end gap-1.5 px-2 py-1.5">
        {/* + Attach button */}
        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => {
              setAttachMenuOpen((v) => !v);
              setPermissionMenuOpen(false);
            }}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-on-surface-variant/60 hover:text-on-surface hover:bg-surface-container transition-colors"
            title="Attach"
          >
            <LegacyIcon name="add" className="text-[19px]" />
          </button>

          {attachMenuOpen && (
            <div className="absolute bottom-full left-0 mb-2 w-52 bg-white border border-outline-variant rounded-xl shadow-xl py-1.5 z-50 animate-in fade-in slide-in-from-bottom-1 duration-150">
              {/* Add attachment (local) */}
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

              {/* @mention project file */}
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

              {/* #session */}
              <button
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2 text-[12px] text-on-surface hover:bg-surface-container-low transition-colors text-left"
                onClick={() => {
                  setAttachMenuOpen(false);
                  setSessionPickerOpen(true);
                  setSessionFilter('');
                }}
              >
                <LegacyIcon name="chat_bubble" className="text-[17px] text-on-surface-variant" />
                Insert # session
              </button>

              {/* /command */}
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
          )}
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          data-testid="chat-input"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          className="w-full border-none focus:ring-0 text-[13px] text-on-surface bg-transparent py-1.5 resize-none min-h-[36px] max-h-[140px] placeholder:text-on-surface-variant/60 outline-none leading-relaxed"
          placeholder={
            isMultiAgent && selectedWorkflowId
              ? t('Describe what you want this workflow to do...')
              : isMultiAgent
              ? t('Ask @Builder, @Orchestrator or trigger @Workflow...')
              : t('Ask your AI Agent anything...')
          }
          rows={1}
        />

        {/* Right controls */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {/* Permission mode button */}
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

            {permissionMenuOpen && (
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
                        {mode.id === permissionMode && (
                          <LegacyIcon name="check" className="text-[14px] text-primary" />
                        )}
                      </div>
                      <span className="text-[10.5px] text-on-surface-variant/70">{mode.description}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Send / Stop button */}
          <button
            type="button"
            data-testid={isRunning && isPlainLlmChat ? 'chat-stop' : 'chat-send'}
            onClick={isRunning && isPlainLlmChat ? onStopRun : handleSend}
            disabled={!canSend && !(isRunning && isPlainLlmChat)}
            className={`w-8 h-8 flex items-center justify-center rounded-full transition-all ${
              isRunning && isPlainLlmChat
                ? 'bg-neutral-900 text-white hover:bg-black'
                : canSend
                ? 'bg-primary text-white hover:opacity-90'
                : 'bg-surface-container text-on-surface-variant/40 cursor-not-allowed'
            }`}
          >
            <LegacyIcon
              name={isRunning && isPlainLlmChat ? 'stop' : 'arrow_upward'}
              className="text-[17px]"
            />
          </button>
        </div>
      </div>

      {/* ── Skill picker popover ── */}
      {skillPickerOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-150"
          style={{ bottom: '100%', left: 0 }}
        >
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="terminal" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">Skills / Commands</span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredSkills.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">
                {skills.length === 0 ? 'No skills loaded' : 'No matches'}
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
                  {skill.desc && (
                    <span className="text-[10.5px] text-on-surface-variant/60 truncate">{skill.desc}</span>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Session picker popover ── */}
      {sessionPickerOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-150">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2">
              <LegacyIcon name="chat_bubble" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">Sessions</span>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredSessions.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">No sessions yet</p>
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
                  <span className="text-[10px] text-on-surface-variant/50">
                    {session.started_at ? new Date(session.started_at).toLocaleDateString() : ''}
                    {session.workflow_id ? ` · ${session.workflow_id}` : ''}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Project file browser popover ── */}
      {fileBrowserOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-72 bg-white border border-outline-variant rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-1 duration-150">
          <div className="p-2 border-b border-outline-variant/30">
            <div className="flex items-center gap-2 px-2 pb-1">
              <LegacyIcon name="folder_open" className="text-[15px] text-on-surface-variant" />
              <span className="text-[11px] font-semibold text-on-surface-variant">Project Files</span>
            </div>
            <input
              type="text"
              value={fileFilter}
              onChange={(e) => setFileFilter(e.target.value)}
              placeholder="Filter files..."
              className="w-full text-[11px] px-2 py-1.5 bg-surface-container rounded-lg border-none outline-none text-on-surface placeholder:text-on-surface-variant/50"
              autoFocus
            />
          </div>
          <div className="max-h-52 overflow-y-auto">
            {filteredFiles.length === 0 ? (
              <p className="px-4 py-3 text-[11px] text-on-surface-variant/60 italic">
                {allFilePaths.length === 0 ? 'No workspace files loaded' : 'No matches'}
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
      )}
    </div>
  );
};
