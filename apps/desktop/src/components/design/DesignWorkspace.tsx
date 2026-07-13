import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  useReactFlow,
  ReactFlowProvider,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  type OnNodesChange,
  MarkerType,
  applyNodeChanges,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  ArrowUp,
  Check,
  Code2,
  FileText,
  ChevronDown,
  ChevronRight,
  Globe,
  History,
  ImagePlus,
  Loader2,
  Mic,
  Monitor,
  Palette,
  Pencil,
  Plus,
  Smartphone,
  Sparkles,
  X,
} from 'lucide-react';
import {
  CanvasSelection,
  ElementSelection,
  IteratePending,
  SpecData,
  UiData,
  LAYOUT,
  IN_FLIGHT,
  DEVICE_VIEW,
  deviceView,
  hostFromUrl,
  inferIterateModeClient,
  buildCanvasNodes,
  buildCanvasEdges,
  isWelcomeSession,
  autoPromptForMd,
  autoPromptForUrl,
  uiCanvasPos,
  selectionKindFromNodeId,
  selectionLabel,
  DesignSystemId,
  DESIGN_SYSTEM_PRESETS,
  DESIGN_ROW_Y,
  DESIGN_CARD_GAP,
} from './designWorkspaceUtils';
import { AgentLogCardNode } from './nodes/AgentLogCardNode';
import { SpecCardNode } from './nodes/SpecCardNode';
import { UiCardNode } from './nodes/UiCardNode';
import { RefCardNode } from './nodes/RefCardNode';
import { MdDocCardNode } from './nodes/MdDocCardNode';
import { UrlCardNode } from './nodes/UrlCardNode';


import { useLanguage } from '../LanguageContext';
import { BTN_PRIMARY, BTN_SECONDARY, BTN_SUCCESS } from '../ui/buttonStyles';
import { APP_INPUT_DOCK_BOTTOM_PX } from '../../constants/layout';
import {
  approveDesignPrototype,
  approveDesignReact,
  designScreenVersionPath,
  ensureDesignSession,
  generateDesignReact,
  generateDesignSession,
  getDesignScreenHtml,
  getDesignSession,
  iterateDesignSession,
  parseDesignRounds,
  sendDesignToCoding,
  startDesignPreview,
  stopDesignPreview,
  stripDesignIterateMeta,
  versionedDesignScreenId,
  type CodingHandoff,
  type DesignRound,
  type DesignSession,
  type DesignSpec,
} from '../../services/designApi';
import { clutchStore } from '../../services/clutchState';
import { sidecarAuthedHttpUrl } from '../../services/sidecarUrl';

type DesignWorkspaceProps = {
  runId: string;
  workspaceReady: boolean;
  modelLabel?: string;
  onOpenModels?: () => void;
  onSendToCoding: (handoff: CodingHandoff) => void;
  onSessionTitle?: (title: string, meta?: { device?: 'web' | 'app' }) => void;
  /** Sidebar spinner: true while generating / iterating. */
  onBusyChange?: (busy: boolean, meta?: { device?: 'web' | 'app' }) => void;
};


function roundTabLabel(prompt: string, index: number): string {
  const trimmed = prompt.trim();
  const label = `Round ${index + 1}`;
  if (!trimmed) return label;
  const snippet = trimmed.length > 32 ? `${trimmed.slice(0, 32)}…` : trimmed;
  return `${label}: ${snippet}`;
}

function DesignRoundSelector({
  rounds,
  selectedRoundIndex,
  onSelect,
}: {
  rounds: DesignRound[];
  selectedRoundIndex: number;
  onSelect: (index: number) => void;
}) {
  const { t } = useLanguage();
  if (rounds.length <= 1) return null;
  return (
    <div
      className="pointer-events-auto mx-auto flex w-full max-w-3xl items-center gap-2 rounded-2xl border border-outline-variant/30 bg-white/92 px-2.5 py-2 shadow-md backdrop-blur-md"
      data-testid="design-round-selector"
    >
      <span className="inline-flex shrink-0 items-center gap-1 px-1 text-[10px] font-bold uppercase tracking-wider text-neutral-400">
        <History size={12} />
        {t('Rounds')}
      </span>
      <div className="flex min-w-0 flex-1 gap-1 overflow-x-auto pb-0.5">
        {rounds.map((round) => {
          const active = round.index === selectedRoundIndex;
          return (
            <button
              key={round.index}
              type="button"
              title={round.user_prompt || `Round ${round.index}`}
              onClick={() => onSelect(round.index)}
              className={`shrink-0 rounded-full border px-3 py-1 text-[11px] font-medium transition-colors ${
                active
                  ? 'border-neutral-900 bg-neutral-900 text-white shadow-sm'
                  : 'border-neutral-200 bg-neutral-50 text-neutral-600 hover:border-neutral-300 hover:bg-white'
              }`}
              data-testid={`design-round-tab-${round.index}`}
            >
              {roundTabLabel(round.user_prompt, round.index)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const nodeTypes = {
  agentLog: AgentLogCardNode,
  spec: SpecCardNode,
  ui: UiCardNode,
  reference: RefCardNode,
  mdDoc: MdDocCardNode,
  urlCard: UrlCardNode,
};

function FitViewOnNodes({
  layoutKey,
  focusIds,
}: {
  layoutKey: string;
  focusIds?: string[];
}) {
  const { fitView, getNodes } = useReactFlow();
  useEffect(() => {
    if (!layoutKey) return;
    const id = window.setTimeout(() => {
      const all = getNodes();
      const targets =
        focusIds && focusIds.length > 0
          ? all.filter((n) => focusIds.includes(n.id))
          : all;
      void fitView({
        nodes: targets.length > 0 ? targets : undefined,
        padding: focusIds?.length ? 0.35 : 0.22,
        maxZoom: focusIds?.length ? 1.05 : 1,
        minZoom: 0.35,
        duration: 320,
      });
    }, 60);
    return () => window.clearTimeout(id);
  }, [layoutKey, focusIds, fitView, getNodes]);
  return null;
}



function DesignCanvasInner({
  runId,
  modelLabel,
  onOpenModels,
  onSendToCoding,
  onSessionTitle,
  onBusyChange,
}: Omit<DesignWorkspaceProps, 'workspaceReady'>) {
  const { t } = useLanguage();
  const [session, setSession] = useState<DesignSession | null>(null);
  const [prompt, setPrompt] = useState('');
  const [referenceImage, setReferenceImage] = useState<{ name: string; dataUrl: string } | null>(null);
  const [referenceMd, setReferenceMd] = useState<{ name: string; text: string } | null>(null);
  const [referenceUrl, setReferenceUrl] = useState<string | null>(null);
  const [urlDraft, setUrlDraft] = useState('');
  const [showUrlField, setShowUrlField] = useState(false);
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [designSystem, setDesignSystem] = useState<DesignSystemId>('clutch');
  const [designSystemMenuOpen, setDesignSystemMenuOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const mdInputRef = useRef<HTMLInputElement | null>(null);
  const [device, setDevice] = useState<'web' | 'app'>('web');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [iterateText, setIterateText] = useState('');
  const [iteratePending, setIteratePending] = useState<IteratePending | null>(null);
  const [focusNodeIds, setFocusNodeIds] = useState<string[] | undefined>(undefined);
  const [showCodeTray, setShowCodeTray] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [welcomeMode, setWelcomeMode] = useState(true);
  const [canvasSelection, setCanvasSelection] = useState<CanvasSelection | null>(null);
  const [elementSelection, setElementSelection] = useState<ElementSelection | null>(null);
  const [pickMode, setPickMode] = useState(false);
  const [selectedRoundIndex, setSelectedRoundIndex] = useState(0);
  const [roundHtmlByScreen, setRoundHtmlByScreen] = useState<Record<string, string | undefined>>({});
  const roundPinnedRef = useRef(false);
  const selectedRoundRef = useRef(0);
  const clipboardRef = useRef<CanvasSelection | null>(null);
  const canvasSelectionRef = useRef<CanvasSelection | null>(null);
  const pickModeRef = useRef(false);
  const iteratePendingRef = useRef<IteratePending | null>(null);
  canvasSelectionRef.current = canvasSelection;
  pickModeRef.current = pickMode;
  iteratePendingRef.current = iteratePending;
  const [nodes, setNodes] = useNodesState<Node>([]);
  const [edges, setEdges] = useEdgesState<Edge>([]);
  const [layoutKey, setLayoutKey] = useState('');
  const pollRef = useRef<number | null>(null);
  const hadSpecRef = useRef(false);
  const hadScreenRef = useRef(false);
  const positionsRef = useRef<Record<string, { x: number; y: number }>>({});
  const userDraggedRef = useRef(false);
  const drawingRef = useRef(false);
  const promptRef = useRef('');
  const designLogKeysRef = useRef<Set<string>>(new Set());

  drawingRef.current = drawing;
  promptRef.current = prompt;
  selectedRoundRef.current = selectedRoundIndex;
  const lastBusyRef = useRef<boolean | null>(null);
  const currentRunIdRef = useRef(runId);
  currentRunIdRef.current = runId;


  useEffect(() => {
    const waitingHtml =
      session?.status === 'ready' && !session.screens?.some((s) => Boolean(s.html));
    const generating =
      busy || Boolean(session && IN_FLIGHT.has(session.status)) || Boolean(waitingHtml);
    if (lastBusyRef.current === generating) return;
    lastBusyRef.current = generating;
    onBusyChange?.(generating, { device });
  }, [busy, session?.status, session?.screens, onBusyChange, device]);

  const stopPoll = useCallback(() => {
    if (pollRef.current != null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const publishRoundLogs = useCallback((round: DesignRound | null) => {
    clutchStore.clearTerminalLogs();
    if (!round) return;
    if (round.reasoning_content?.trim()) {
      clutchStore.appendTerminalLog(
        `[DESIGN:REASONING] ${round.reasoning_content.trim().replace(/\n/g, ' ↵ ')}`,
      );
    }
    if (round.user_prompt.trim()) {
      clutchStore.appendTerminalLog(`[USER] ${round.user_prompt}`);
    }
    for (const entry of round.entries) {
      if (!entry.text?.trim()) continue;
      const statusBit = entry.status ? ` · ${entry.status}` : '';
      clutchStore.appendTerminalLog(`[DESIGN] ${entry.text}${statusBit}`);
    }
  }, []);

  const syncDesignTerminalLogs = useCallback(
    (next: DesignSession, roundIndex: number) => {
      const rounds = parseDesignRounds(next.process_log, next.rounds, next.round_history);
      const round = rounds.find((r) => r.index === roundIndex) ?? rounds[rounds.length - 1] ?? null;
      publishRoundLogs(round);

      const stamp = () => {
        const d = new Date();
        const pad = (n: number) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
      };
      const htmlCount = (next.screens || []).filter((s) => Boolean(s.html)).length;
      const statusKey = `status:${next.status}:screens=${next.screens?.length || 0}:html=${htmlCount}:round=${roundIndex}`;
      if (!designLogKeysRef.current.has(statusKey)) {
        designLogKeysRef.current.add(statusKey);
        clutchStore.appendTerminalLog(
          `[${stamp()}] [DESIGN] status=${next.status} round=${roundIndex} screens=${next.screens?.length || 0} html=${htmlCount}${
            next.ui_preview_url ? ` preview=${next.ui_preview_url}` : ''
          }`,
        );
      }
    },
    [publishRoundLogs],
  );

  const syncNodesFromSession = useCallback(
    (
      next: DesignSession | null,
      nextPrompt: string,
      nextDrawing: boolean,
      extras?: {
        referenceImageUrl?: string | null;
        referenceMd?: { name: string; text: string } | null;
        referenceUrl?: string | null;
      },
    ) => {
      const selectedId = canvasSelectionRef.current?.nodeId ?? null;
      const built = buildCanvasNodes(
        next,
        nextPrompt,
        nextDrawing,
        userDraggedRef.current ? positionsRef.current : {},
        {
          referenceImageUrl:
            extras?.referenceImageUrl ?? next?.reference_image_url ?? referenceImage?.dataUrl,
          referenceMd: extras?.referenceMd ?? (next?.reference_md_text
            ? { name: next.reference_md_name || 'DESIGN.md', text: next.reference_md_text }
            : referenceMd),
          referenceUrl: extras?.referenceUrl ?? next?.reference_url ?? referenceUrl,
          pickMode,
          selectedElementLabel: elementSelection?.label ?? null,
          selectedElementPath: elementSelection?.path ?? null,
          pickScreenId: canvasSelectionRef.current?.screenId || elementSelection?.screenId || null,
          selectedNodeId: selectedId,
          iteratePending: iteratePendingRef.current,
          selectedRoundIndex,
          roundHtmlByScreen,
          runId,
          onTogglePick: ({ nodeId, screenId, name }) => {
            const already =
              canvasSelectionRef.current?.nodeId === nodeId && pickModeRef.current;
            setCanvasSelection({
              nodeId,
              kind: 'ui',
              label: name,
              screenId,
            });
            setNodes((nds) => nds.map((n) => ({ ...n, selected: n.id === nodeId })));
            if (already) {
              setPickMode(false);
            } else {
              setPickMode(true);
              setElementSelection(null);
            }
          },
        },
      );
      for (const node of built) {
        // Default layout is authoritative until the user drags a card.
        if (userDraggedRef.current && positionsRef.current[node.id]) {
          const saved = positionsRef.current[node.id];
          node.position = {
            x: saved.x,
            y: node.id === 'agentLog' || node.id === 'spec' || node.id.startsWith('ui')
              ? DESIGN_ROW_Y
              : saved.y,
          };
        } else {
          positionsRef.current[node.id] = { ...node.position };
        }
        node.selected = node.id === selectedId;
      }
      setNodes(built);
      setEdges(buildCanvasEdges(built));
      const key = built.map((n) => n.id).join('-');
      if (key && !userDraggedRef.current) {
        setLayoutKey(`${key}-${next?.status || ''}`);
      }
    },
    [
      setNodes,
      setEdges,
      t,
      referenceImage?.dataUrl,
      referenceMd,
      referenceUrl,
      pickMode,
      elementSelection?.label,
      elementSelection?.screenId,
      elementSelection?.path,
      iteratePending,
      selectedRoundIndex,
      roundHtmlByScreen,
      runId,
    ],
  );

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      setNodes((nds) => {
        const next = applyNodeChanges(changes, nds);
        for (const change of changes) {
          if (change.type === 'position' && change.position && change.id) {
            positionsRef.current[change.id] = { ...change.position };
            if (change.dragging === false) {
              userDraggedRef.current = true;
            }
          }
        }
        return next;
      });
    },
    [setNodes],
  );

  const applySession = useCallback(
    (next: DesignSession) => {
      if (next.run_id !== currentRunIdRef.current && next.id !== currentRunIdRef.current) {
        return;
      }
      const rounds = parseDesignRounds(next.process_log, next.rounds, next.round_history);
      const latestRoundIndex = rounds[rounds.length - 1]?.index ?? 0;
      const effectiveRoundIndex =
        !roundPinnedRef.current || !rounds.some((r) => r.index === selectedRoundRef.current)
          ? latestRoundIndex
          : selectedRoundRef.current;
      setSession(next);
      setSelectedRoundIndex(effectiveRoundIndex);
      setPreviewUrl(next.preview_url ?? null);
      if (next.device === 'app' || next.device === 'web') {
        setDevice(next.device);
      }
      if (next.prompt) setPrompt(next.prompt);
      if (next.reference_image_url) {
        setReferenceImage((prev) => prev ?? { name: 'image.png', dataUrl: next.reference_image_url! });
      }
      if (next.reference_md_text) {
        setReferenceMd((prev) =>
          prev ?? {
            name: next.reference_md_name || 'DESIGN.md',
            text: next.reference_md_text!,
          },
        );
      }
      if (next.reference_url) {
        setReferenceUrl((prev) => prev ?? next.reference_url!);
      }
      const hasSource = Boolean(
        next.reference_image_url || next.reference_md_text || next.reference_url,
      );
      const hasHtml = Boolean(next.screens?.some((s) => Boolean(s.html)));
      const hasCanvas = Boolean(
        next.spec || next.screens?.length || IN_FLIGHT.has(next.status) || hasSource,
      );
      setWelcomeMode(isWelcomeSession(next) || (!hasCanvas && !next.prompt?.trim() && !hasSource));
      if (next.error) setError(next.error);
      if (next.spec && !hadSpecRef.current) {
        hadSpecRef.current = true;
      }
      let nextDrawing = drawingRef.current;
      if (hasHtml && !hadScreenRef.current) {
        hadScreenRef.current = true;
        nextDrawing = true;
        setDrawing(true);
        window.setTimeout(() => setDrawing(false), 1450);
      }
      // Sidebar spinner must track real UI hydrate, not just status=ready.
      if (next.status === 'error') {
        setBusy(false);
      } else if (next.status === 'ready' && hasHtml) {
        setBusy(false);
      } else if (IN_FLIGHT.has(next.status) || (next.status === 'ready' && !hasHtml)) {
        setBusy(true);
      }
      syncDesignTerminalLogs(next, effectiveRoundIndex);
      if (isWelcomeSession(next) && !hasSource) {
        setBusy(false);
        setNodes([]);
        setEdges([]);
        return;
      }
      syncNodesFromSession(next, next.prompt || promptRef.current, nextDrawing, {
        referenceImageUrl: next.reference_image_url,
        referenceMd: next.reference_md_text
          ? { name: next.reference_md_name || 'DESIGN.md', text: next.reference_md_text }
          : null,
        referenceUrl: next.reference_url,
      });
    },
    [syncNodesFromSession, setNodes, setEdges, syncDesignTerminalLogs],
  );

  const enrichSessionHtml = useCallback(async (next: DesignSession): Promise<DesignSession> => {
    const screens = next.screens || [];
    if (!screens.some((s) => s.id && !s.html)) return next;
    const filled = await Promise.all(
      screens.map(async (screen) => {
        if (screen.html || !screen.id) return screen;
        try {
          const html = await getDesignScreenHtml(runId, screen.id);
          if (!html?.trim()) return screen;
          return { ...screen, html };
        } catch {
          return screen;
        }
      }),
    );
    return { ...next, screens: filled };
  }, [runId]);

  const startPoll = useCallback(() => {
    stopPoll();
    let ticks = 0;
    pollRef.current = window.setInterval(() => {
      ticks += 1;
      void getDesignSession(runId)
        .then(async (raw) => {
          const next = await enrichSessionHtml(raw);
          applySession(next);
          const hasHtml = Boolean(next.screens?.some((s) => Boolean(s.html)));
          if (next.status === 'error') {
            stopPoll();
            return;
          }
          if (next.status === 'ready' && hasHtml) {
            stopPoll();
            return;
          }
          // ready without html: keep polling briefly (folder rename / write race).
          if (next.status === 'ready' && !hasHtml && ticks >= 25) {
            stopPoll();
            setBusy(false);
            setError((prev) => prev || 'Interface HTML not available yet — try reopening the session.');
            clutchStore.appendTerminalLog(
              '[DESIGN] ready but screen HTML missing after poll timeout',
            );
          }
          if (ticks >= 120) {
            stopPoll();
            setBusy(false);
          }
        })
        .catch((err) => {
          clutchStore.appendTerminalLog(
            `[DESIGN] poll error: ${err instanceof Error ? err.message : String(err)}`,
          );
        });
    }, 900);
  }, [runId, applySession, stopPoll, enrichSessionHtml]);

  const hydrate = useCallback(async () => {
    if (!runId) return;
    try {
      designLogKeysRef.current = new Set();
      await ensureDesignSession({ run_id: runId, title: t('New Design') });
      const raw = await getDesignSession(runId);
      const next = await enrichSessionHtml(raw);
      hadSpecRef.current = Boolean(next.spec);
      hadScreenRef.current = Boolean(next.screens?.[0]?.html);
      userDraggedRef.current = false;
      positionsRef.current = {};
      applySession(next);
      const waitingHtml =
        next.status === 'ready' && !next.screens?.some((s) => Boolean(s.html));
      if (IN_FLIGHT.has(next.status) || waitingHtml) {
        setBusy(true);
        setWelcomeMode(false);
        startPoll();
      } else if (isWelcomeSession(next)) {
        setBusy(false);
        setWelcomeMode(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [runId, t, applySession, startPoll, enrichSessionHtml]);

  useEffect(() => {
    // Reset surface immediately when switching Design sessions.
    setWelcomeMode(true);
    setSession(null);
    setPrompt('');
    setReferenceImage(null);
    setReferenceMd(null);
    setReferenceUrl(null);
    setUrlDraft('');
    setShowUrlField(false);
    setAttachMenuOpen(false);
    setCanvasSelection(null);
    setElementSelection(null);
    setPickMode(false);
    setNodes([]);
    setEdges([]);
    setBusy(false);
    setError(null);
    setDrawing(false);
    setIterateText('');
    setShowCodeTray(false);
    setPreviewUrl(null);
    setSelectedRoundIndex(0);
    setRoundHtmlByScreen({});
    roundPinnedRef.current = false;
    selectedRoundRef.current = 0;
    hadSpecRef.current = false;
    hadScreenRef.current = false;
    userDraggedRef.current = false;
    positionsRef.current = {};
    lastBusyRef.current = null;
    stopPoll();
    void hydrate();
    return () => stopPoll();
  }, [runId]); // eslint-disable-line react-hooks/exhaustive-deps -- remount surface per session

  useEffect(() => {
    if (welcomeMode || !session) return;
    syncNodesFromSession(session, prompt, drawing);
  }, [drawing]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (welcomeMode || !session) return;
    syncNodesFromSession(session, prompt, drawing, {
      referenceImageUrl: referenceImage?.dataUrl,
      referenceMd,
      referenceUrl,
    });
  }, [referenceImage?.dataUrl, referenceMd, referenceUrl, pickMode, elementSelection?.label, elementSelection?.path]); // eslint-disable-line react-hooks/exhaustive-deps

  const designRounds = parseDesignRounds(session?.process_log, session?.rounds, session?.round_history);

  const handleRoundSelect = useCallback(
    (index: number) => {
      roundPinnedRef.current = true;
      setSelectedRoundIndex(index);
      if (session) {
        const rounds = parseDesignRounds(session.process_log, session.rounds, session.round_history);
        const round = rounds.find((r) => r.index === index) ?? null;
        publishRoundLogs(round);
      }
    },
    [session, publishRoundLogs],
  );

  useEffect(() => {
    if (welcomeMode || !session) return;
    const screens = session.screens || [];
    if (!screens.length) return;
    let cancelled = false;

    void (async () => {
      const nextMap: Record<string, string | undefined> = {};
      await Promise.all(
        screens.map(async (screen) => {
          const screenId = screen.id || 'main';
          const versionedId = versionedDesignScreenId(screenId, selectedRoundIndex);
          try {
            const html = await getDesignScreenHtml(runId, versionedId);
            if (html?.trim()) {
              nextMap[screenId] = html;
              return;
            }
          } catch {
            // Versioned screen not persisted yet — fall back below.
          }
          if (screen.html?.trim()) {
            nextMap[screenId] = screen.html;
            return;
          }
          try {
            const html = await getDesignScreenHtml(runId, screenId);
            if (html?.trim()) nextMap[screenId] = html;
          } catch {
            nextMap[screenId] = screen.html;
          }
        }),
      );
      if (!cancelled) setRoundHtmlByScreen(nextMap);
    })();

    return () => {
      cancelled = true;
    };
  }, [welcomeMode, session, selectedRoundIndex, runId]);

  const withBusy = async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
      return undefined;
    }
  };

  const addImageFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      setReferenceImage({ name: file.name || 'image.png', dataUrl: reader.result as string });
      setReferenceMd(null);
      setReferenceUrl(null);
      setShowUrlField(false);
    };
    reader.readAsDataURL(file);
  }, []);

  const addMdFile = useCallback((file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      const name = file.name || 'DESIGN.md';
      const text = String(reader.result || '');
      setReferenceMd({ name, text });
      setReferenceImage(null);
      setReferenceUrl(null);
      setShowUrlField(false);
      setPrompt((prev) => {
        const trimmed = prev.trim();
        if (!trimmed || /使用 the file \[/.test(trimmed) || /Use the file \[/.test(trimmed)) {
          return autoPromptForMd(name);
        }
        return prev;
      });
    };
    reader.readAsText(file);
  }, []);

  const commitUrl = useCallback((raw: string) => {
    const value = raw.trim();
    if (!value) return;
    const normalized = /^https?:\/\//i.test(value) ? value : `https://${value}`;
    setReferenceUrl(normalized);
    setReferenceImage(null);
    setReferenceMd(null);
    setShowUrlField(false);
    setUrlDraft('');
    setPrompt((prev) => (prev.trim() ? prev : autoPromptForUrl()));
  }, []);

  const handlePasteImage = useCallback(
    (e: React.ClipboardEvent) => {
      const text = e.clipboardData.getData('text/plain')?.trim();
      if (text && /^https?:\/\/\S+$/i.test(text)) {
        e.preventDefault();
        commitUrl(text);
        return;
      }
      const { files } = e.clipboardData;
      if (!files || files.length === 0) return;
      for (const file of Array.from(files)) {
        if (file.type.startsWith('image/')) {
          e.preventDefault();
          addImageFile(file);
          return;
        }
      }
    },
    [addImageFile, commitUrl],
  );

  const handleGenerate = async () => {
    const hasRef = Boolean(referenceImage || referenceMd || referenceUrl);
    const text =
      prompt.trim() ||
      (referenceMd
        ? autoPromptForMd(referenceMd.name)
        : referenceUrl
          ? autoPromptForUrl()
          : referenceImage
            ? t('Match this reference UI')
            : '');
    if (!text && !hasRef) return;
    setWelcomeMode(false);
    setBusy(true);
    setError(null);
    setAttachMenuOpen(false);
    setDesignSystemMenuOpen(false);
    hadSpecRef.current = false;
    hadScreenRef.current = false;
    userDraggedRef.current = false;
    positionsRef.current = {};
    designLogKeysRef.current = new Set();
    roundPinnedRef.current = false;
    clutchStore.appendTerminalLog(
      `[DESIGN] generate requested device=${device} prompt=${JSON.stringify((text || '').slice(0, 80))}`,
    );
    onSessionTitle?.(text.slice(0, 48) || t('New Design'), { device });
    const next = await withBusy(() =>
      generateDesignSession(runId, {
        prompt: text || '生成设计系统与界面',
        device,
        reference_image: referenceImage?.dataUrl ?? null,
        reference_md: referenceMd?.text ?? null,
        reference_md_name: referenceMd?.name ?? null,
        reference_url: referenceUrl,
        design_system: hasRef ? undefined : designSystem,
      }),
    );
    if (next) {
      applySession(next);
      startPoll();
    } else {
      setBusy(false);
    }
  };

  const handleIterate = async () => {
    if (!iterateText.trim() || !session) return;
    const instruction = iterateText.trim();
    const mode = inferIterateModeClient(instruction, canvasSelection?.kind ?? 'ui');
    const targetId =
      canvasSelection?.screenId ?? session.screens?.[0]?.id ?? null;
    const now = new Date().toISOString();
    const pending: IteratePending = { mode, screenId: targetId };
    setIteratePending(pending);
    iteratePendingRef.current = pending;
    roundPinnedRef.current = false;
    setDrawing(true);
    setBusy(true);
    setError(null);
    // Focus spec / target screen; execution status lives in Agent Log.
    userDraggedRef.current = false;
    const iterateFocusId =
      mode === 'modify' && targetId
        ? `ui-${targetId}`
        : session.spec
          ? 'spec'
          : session.screens?.[0]?.id
            ? `ui-${session.screens[0].id}`
            : 'spec';
    setFocusNodeIds([iterateFocusId]);
    setCanvasSelection({
      nodeId: iterateFocusId,
      kind: iterateFocusId.startsWith('ui') ? 'ui' : 'spec',
      label:
        iterateFocusId.startsWith('ui')
          ? session.screens?.find((s) => `ui-${s.id}` === iterateFocusId)?.name || 'Interface'
          : String(session.spec?.name || 'Design system'),
      screenId: iterateFocusId.startsWith('ui')
        ? iterateFocusId.replace(/^ui-/, '')
        : undefined,
    });
    const optimistic: DesignSession = {
      ...session,
      status: 'iterating',
      process_log: [
        ...(session.process_log || []),
        { role: 'user', text: instruction, at: now },
        {
          role: 'assistant',
          text:
            mode === 'add'
              ? 'Creating a new version…'
              : 'Thinking… applying your changes to the selected design.',
          status: 'iterating',
          at: now,
        },
      ],
    };
    setSession(optimistic);
    syncNodesFromSession(optimistic, optimistic.prompt || prompt, true);
    setLayoutKey(`iterate-start-${Date.now()}`);

    const next = await withBusy(() =>
      iterateDesignSession(runId, instruction, {
        target_kind: canvasSelection?.kind ?? 'ui',
        target_id: targetId,
        element_path: elementSelection?.path ?? null,
        element_label: elementSelection?.label ?? null,
        mode,
      }),
    );
    if (next) {
      const action = next.last_iterate_action;
      const focusScreen =
        next.last_iterate_screen_id ||
        targetId ||
        next.screens?.[next.screens.length - 1]?.id;
      setIterateText('');
      setPickMode(false);
      setIteratePending(null);
      iteratePendingRef.current = null;
      applySession(next);
      setDrawing(true);
      window.setTimeout(() => setDrawing(false), 1450);
      setBusy(false);
      userDraggedRef.current = false;
      const focusId = focusScreen ? `ui-${focusScreen}` : 'spec';
      setFocusNodeIds([focusId]);
      setLayoutKey(`iterate-done-${Date.now()}-${action || mode}`);
      setCanvasSelection({
        nodeId: focusId,
        kind: 'ui',
        label: next.screens?.find((s) => s.id === focusScreen)?.name || 'Interface',
        screenId: focusScreen || undefined,
      });
    } else {
      setIteratePending(null);
      iteratePendingRef.current = null;
      setDrawing(false);
      setBusy(false);
      setFocusNodeIds(undefined);
    }
  };

  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes }: { nodes: Node[] }) => {
      const node = selectedNodes[0];
      if (!node) return;
      const kind = selectionKindFromNodeId(node.id);
      const data = node.data as UiData;
      setCanvasSelection({
        nodeId: node.id,
        kind,
        label: selectionLabel(kind, node, session),
        screenId: data.screenId || (kind === 'ui' ? session?.screens?.[0]?.id : undefined),
      });
      if (kind !== 'ui') {
        setPickMode(false);
        setElementSelection(null);
      }
    },
    [session],
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const kind = selectionKindFromNodeId(node.id);
      const data = node.data as UiData;
      setCanvasSelection({
        nodeId: node.id,
        kind,
        label: selectionLabel(kind, node, session),
        screenId: data.screenId || (kind === 'ui' ? session?.screens?.[0]?.id : undefined),
      });
      if (kind !== 'ui') {
        setPickMode(false);
        setElementSelection(null);
      }
    },
    [session],
  );

  const onPaneClick = useCallback(() => {
    setCanvasSelection(null);
    setElementSelection(null);
    setPickMode(false);
    setNodes((nds) => nds.map((n) => ({ ...n, selected: false })));
  }, [setNodes]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const data = event.data as { source?: string; path?: string; label?: string };
      if (data?.source !== 'clutch-design-pick' || !data.path) return;
      setElementSelection({
        path: data.path,
        label: data.label || data.path,
        screenId: canvasSelection?.screenId || session?.screens?.[0]?.id,
      });
      setPickMode(false);
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [canvasSelection?.screenId, session?.screens]);

  useEffect(() => {
    if (welcomeMode) return;
    const onKey = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;
      if (!meta) return;
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
      if (e.key === 'c' && canvasSelection) {
        e.preventDefault();
        clipboardRef.current = canvasSelection;
      }
      if (e.key === 'v' && clipboardRef.current) {
        e.preventDefault();
        const clip = clipboardRef.current;
        if (clip.kind === 'ui') {
          setIterateText((prev) => prev || t('Create another screen based on the selection'));
          setCanvasSelection(clip);
          void (async () => {
            setDrawing(true);
            setBusy(true);
            const next = await withBusy(() =>
              iterateDesignSession(runId, t('Create another screen based on the selection'), {
                target_kind: 'ui',
                target_id: clip.screenId ?? null,
                mode: 'add',
              }),
            );
            if (next) {
              applySession(next);
              setBusy(false);
              setDrawing(false);
            } else {
              setBusy(false);
              setDrawing(false);
            }
          })();
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [welcomeMode, canvasSelection, runId, t, applySession]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      {welcomeMode ? (
        <div className="relative z-10 flex h-full flex-col items-center justify-center px-6">
          <h1 className="mb-8 text-2xl font-bold tracking-tight text-neutral-900">
            {t('Welcome to Design')}
          </h1>
          <div
            className="w-full max-w-2xl rounded-[28px] border border-neutral-200/80 bg-white/90 p-4 shadow-lg backdrop-blur-md"
            onPaste={handlePasteImage}
            onDragOver={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const files = Array.from(e.dataTransfer.files);
              const md = files.find((f) => /\.(md|markdown|txt)$/i.test(f.name));
              if (md) {
                addMdFile(md);
                return;
              }
              const img = files.find((f) => f.type.startsWith('image/'));
              if (img) addImageFile(img);
            }}
          >
            {(referenceImage || referenceMd || referenceUrl) && (
              <div className="mb-2 flex flex-wrap items-center gap-2 px-2">
                {referenceImage ? (
                  <span className="inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 py-1 pl-1.5 pr-2 text-[11px] font-medium text-neutral-700">
                    <img
                      src={referenceImage.dataUrl}
                      alt=""
                      className="h-5 w-5 rounded-full object-cover"
                    />
                    <span className="truncate">{referenceImage.name}</span>
                    <button
                      type="button"
                      className="ml-0.5 rounded-full p-0.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700"
                      onClick={() => setReferenceImage(null)}
                      aria-label={t('Remove reference image')}
                    >
                      <X size={12} />
                    </button>
                  </span>
                ) : null}
                {referenceMd ? (
                  <span className="inline-flex max-w-[260px] items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 py-1 pl-2 pr-2 text-[11px] font-medium text-neutral-700">
                    <FileText size={13} className="shrink-0 text-neutral-500" />
                    <span className="truncate">{referenceMd.name}</span>
                    <button
                      type="button"
                      className="ml-0.5 rounded-full p-0.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700"
                      onClick={() => setReferenceMd(null)}
                      aria-label={t('Remove file')}
                    >
                      <X size={12} />
                    </button>
                  </span>
                ) : null}
                {referenceUrl ? (
                  <span className="inline-flex max-w-[260px] items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-50 py-1 pl-2 pr-2 text-[11px] font-medium text-neutral-700">
                    <Globe size={13} className="shrink-0 text-sky-600" />
                    <span className="truncate">{hostFromUrl(referenceUrl)}</span>
                    <button
                      type="button"
                      className="ml-0.5 rounded-full p-0.5 text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700"
                      onClick={() => setReferenceUrl(null)}
                      aria-label={t('Remove URL')}
                    >
                      <X size={12} />
                    </button>
                  </span>
                ) : null}
              </div>
            )}
            {showUrlField ? (
              <div className="mb-2 flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2">
                <Globe size={14} className="shrink-0 text-neutral-400" />
                <input
                  autoFocus
                  className="min-w-0 flex-1 bg-transparent text-[13px] text-neutral-800 placeholder:text-neutral-400 focus:outline-none"
                  placeholder={t('Paste URL…')}
                  value={urlDraft}
                  onChange={(e) => setUrlDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      commitUrl(urlDraft);
                    }
                    if (e.key === 'Escape') {
                      setShowUrlField(false);
                      setUrlDraft('');
                    }
                  }}
                />
                <button
                  type="button"
                  className="rounded-full bg-neutral-900 px-2.5 py-1 text-[11px] font-semibold text-white disabled:opacity-40"
                  disabled={!urlDraft.trim()}
                  onClick={() => commitUrl(urlDraft)}
                >
                  {t('Add URL')}
                </button>
              </div>
            ) : null}
            <textarea
              className="min-h-[88px] w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-relaxed text-neutral-800 placeholder:text-neutral-400 focus:outline-none"
              placeholder={
                referenceMd || referenceUrl || referenceImage
                  ? t('Describe changes, or send to match the reference')
                  : t('What do you want to design?')
              }
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onPaste={handlePasteImage}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void handleGenerate();
                }
              }}
            />
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) addImageFile(file);
                e.target.value = '';
              }}
            />
            <input
              ref={mdInputRef}
              type="file"
              accept=".md,.markdown,.txt,text/markdown,text/plain"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) addMdFile(file);
                e.target.value = '';
              }}
            />
            <div className="mt-2 flex items-center justify-between gap-2">
              <div className="relative flex items-center gap-1.5">
                <button
                  type="button"
                  className="rounded-full p-2 text-neutral-500 hover:bg-neutral-100"
                  onClick={() => {
                    setDesignSystemMenuOpen(false);
                    setAttachMenuOpen((v) => !v);
                  }}
                  title={t('Add attachment')}
                  aria-label={t('Add attachment')}
                >
                  <Plus size={16} />
                </button>
                {attachMenuOpen ? (
                  <div className="absolute bottom-full left-0 z-30 mb-2 w-48 overflow-hidden rounded-xl border border-neutral-200 bg-white py-1 shadow-lg">
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-neutral-700 hover:bg-neutral-50"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        setShowUrlField(true);
                      }}
                    >
                      <Globe size={14} /> {t('Website URL')}
                    </button>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-neutral-700 hover:bg-neutral-50"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        mdInputRef.current?.click();
                      }}
                    >
                      <FileText size={14} /> {t('Upload file')}
                    </button>
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] text-neutral-700 hover:bg-neutral-50"
                      onClick={() => {
                        setAttachMenuOpen(false);
                        fileInputRef.current?.click();
                      }}
                    >
                      <ImagePlus size={14} /> {t('Upload image')}
                    </button>
                  </div>
                ) : null}
                <button
                  type="button"
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                    device === 'app' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-100'
                  }`}
                  onClick={() => setDevice('app')}
                >
                  <Smartphone size={13} />
                  {t('App')}
                </button>
                <button
                  type="button"
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                    device === 'web' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-100'
                  }`}
                  onClick={() => setDevice('web')}
                >
                  <Monitor size={13} />
                  {t('Web')}
                </button>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="relative">
                  <button
                    type="button"
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold transition-colors ${
                      referenceImage || referenceMd || referenceUrl
                        ? 'cursor-not-allowed text-neutral-300'
                        : designSystemMenuOpen
                          ? 'bg-neutral-100 text-neutral-800'
                          : 'text-neutral-600 hover:bg-neutral-100'
                    }`}
                    disabled={Boolean(referenceImage || referenceMd || referenceUrl)}
                    title={
                      referenceImage || referenceMd || referenceUrl
                        ? t('Reference attachment overrides the design system preset.')
                        : t('Design system')
                    }
                    aria-label={t('Design system')}
                    onClick={() => {
                      if (referenceImage || referenceMd || referenceUrl) return;
                      setAttachMenuOpen(false);
                      setDesignSystemMenuOpen((v) => !v);
                    }}
                  >
                    <Palette size={14} />
                    <span>
                      {t(
                        DESIGN_SYSTEM_PRESETS.find((p) => p.id === designSystem)?.labelKey
                          ?? 'Clutch',
                      )}
                    </span>
                    <ChevronDown size={12} className="opacity-60" />
                  </button>
                  {designSystemMenuOpen && !(referenceImage || referenceMd || referenceUrl) ? (
                    <div className="absolute bottom-full right-0 z-30 mb-2 w-72 overflow-hidden rounded-xl border border-neutral-200 bg-white py-1 shadow-lg">
                      <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
                        {t('Design system')}
                      </p>
                      {DESIGN_SYSTEM_PRESETS.map((preset) => {
                        const active = designSystem === preset.id;
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            className={`flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-neutral-50 ${
                              active ? 'bg-neutral-50' : ''
                            }`}
                            onClick={() => {
                              setDesignSystem(preset.id);
                              setDesignSystemMenuOpen(false);
                            }}
                          >
                            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-neutral-200 bg-gradient-to-br from-neutral-800 via-neutral-500 to-neutral-200" />
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center justify-between gap-2 text-[12px] font-semibold text-neutral-900">
                                {t(preset.labelKey)}
                                {active ? <Check size={14} className="text-sky-600" /> : null}
                              </span>
                              <span className="mt-0.5 block text-[11px] leading-snug text-neutral-500">
                                {t(preset.descriptionKey)}
                              </span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={onOpenModels}
                  className="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-[11px] font-semibold text-neutral-700"
                >
                  <Sparkles size={12} />
                  {modelLabel || 'Model'}
                </button>
                <button type="button" className="rounded-full p-2 text-neutral-400" disabled>
                  <Mic size={15} />
                </button>
                <button
                  type="button"
                  disabled={busy || (!prompt.trim() && !referenceImage && !referenceMd && !referenceUrl)}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-neutral-900 text-white disabled:opacity-40"
                  onClick={() => void handleGenerate()}
                  aria-label="Send"
                >
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} />}
                </button>
              </div>
            </div>
          </div>
          <p className="mt-3 text-center text-[12px] text-neutral-400">
            {t('Attach Design.md, a website URL, or a reference image')}
          </p>
          {error ? (
            <p className="mt-4 max-w-lg text-center text-[12px] text-rose-600">{error}</p>
          ) : null}
        </div>
      ) : (
        <>
          <div className="absolute inset-0 z-0">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onSelectionChange={onSelectionChange}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              nodesDraggable
              nodesConnectable={false}
              elementsSelectable
              panOnDrag={[1, 2]}
              selectionOnDrag={false}
              selectNodesOnDrag={false}
              defaultViewport={{ x: 24, y: 24, zoom: 0.85 }}
              minZoom={0.35}
              maxZoom={1.25}
              panOnScroll
              proOptions={{ hideAttribution: true }}
              className="!bg-transparent"
            >
              <Background gap={18} size={1} color="#d4d4d8" />
              <Controls
                position="bottom-left"
                className="!mb-[4.5rem] !ml-3 !overflow-visible !rounded-xl !border !border-neutral-200 !bg-white/95 !shadow-sm"
              />
              <FitViewOnNodes layoutKey={layoutKey} focusIds={focusNodeIds} />
            </ReactFlow>
          </div>

          <div
            className="pointer-events-none absolute inset-x-0 z-20 flex justify-center px-4"
            style={{ bottom: APP_INPUT_DOCK_BOTTOM_PX + 72 }}
          >
            <DesignRoundSelector
              rounds={designRounds}
              selectedRoundIndex={selectedRoundIndex}
              onSelect={handleRoundSelect}
            />
          </div>

          <div
            className="pointer-events-none absolute inset-x-0 z-20 flex justify-center px-4"
            style={{ bottom: APP_INPUT_DOCK_BOTTOM_PX }}
          >
            <div
              className="pointer-events-auto flex w-full max-w-2xl flex-col gap-1.5 rounded-2xl border border-outline-variant/30 bg-white/90 px-3 py-2 shadow-md backdrop-blur-md"
              onPaste={handlePasteImage}
            >
              {(canvasSelection || elementSelection) && (
                <div className="flex flex-wrap items-center gap-1.5 px-0.5">
                  {canvasSelection ? (
                    <span className="inline-flex max-w-[240px] items-center gap-1 rounded-full border border-outline-variant/40 bg-surface-container-low py-0.5 pl-2 pr-1 text-[11px] font-medium text-on-surface">
                      <span className="shrink-0 text-on-surface-variant">
                        {canvasSelection.kind === 'ui' ? t('Artboard') : t('Selected')}
                      </span>
                      <span className="truncate">{canvasSelection.label}</span>
                      <button
                        type="button"
                        className="rounded-full p-0.5 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                        onClick={() => {
                          setCanvasSelection(null);
                          setElementSelection(null);
                          setPickMode(false);
                          setNodes((nds) => nds.map((n) => ({ ...n, selected: false })));
                        }}
                        aria-label={t('Clear selection')}
                      >
                        <X size={11} />
                      </button>
                    </span>
                  ) : null}
                  {elementSelection ? (
                    <span className="inline-flex max-w-[220px] items-center gap-1 rounded-full border border-outline-variant/40 bg-surface-container-low py-0.5 pl-2 pr-1 text-[11px] font-medium text-on-surface">
                      <span className="shrink-0 text-on-surface-variant">{t('Element')}</span>
                      <span className="truncate">{elementSelection.label}</span>
                      <button
                        type="button"
                        className="rounded-full p-0.5 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                        onClick={() => setElementSelection(null)}
                        aria-label={t('Clear element')}
                      >
                        <X size={11} />
                      </button>
                    </span>
                  ) : null}
                </div>
              )}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-full p-2 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                  onClick={() => fileInputRef.current?.click()}
                  title={t('Paste or attach a reference image')}
                  aria-label={t('Paste or attach a reference image')}
                >
                  <ImagePlus size={15} />
                </button>
                <input
                  className="min-w-0 flex-1 bg-transparent text-[13px] text-on-surface placeholder:text-on-surface-variant/60 focus:outline-none"
                  placeholder={
                    canvasSelection
                      ? t('What do you want to change or create?')
                      : t('Select a card, then describe the change…')
                  }
                  value={iterateText}
                  onChange={(e) => setIterateText(e.target.value)}
                  onPaste={handlePasteImage}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void handleIterate();
                  }}
                />
                <button
                  type="button"
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-semibold transition-colors ${
                    showCodeTray
                      ? 'border-neutral-900 bg-neutral-900 text-white'
                      : 'border-outline-variant/40 bg-surface-container-low text-on-surface-variant hover:border-outline-variant hover:text-on-surface'
                  }`}
                  onClick={() => setShowCodeTray((v) => !v)}
                  title={t('Prototype → Approve → UI code → Coding')}
                  aria-expanded={showCodeTray}
                  aria-label={t('UI code')}
                >
                  <Code2 size={12} className="inline shrink-0" />
                  {t('UI code')}
                </button>
                <button
                  type="button"
                  disabled={busy || !iterateText.trim()}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-900 text-white disabled:opacity-40"
                  onClick={() => void handleIterate()}
                >
                  <ArrowUp size={14} />
                </button>
              </div>
            </div>
          </div>

          {showCodeTray ? (
            <div className="absolute right-4 top-4 z-20 w-[300px] space-y-2 rounded-2xl border border-outline-variant/30 bg-white p-3 shadow-md">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-[12px] font-semibold text-on-surface">{t('UI code')}</p>
                  <p className="text-[10px] text-on-surface-variant">
                    {t('Prototype → Approve → UI code → Coding')}
                  </p>
                </div>
                <button
                  type="button"
                  className="rounded-md p-1 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                  onClick={() => setShowCodeTray(false)}
                  aria-label={t('Close')}
                >
                  <X size={14} />
                </button>
              </div>
              <p className="text-[11px] leading-relaxed text-on-surface-variant">
                {session?.prototype_approved
                  ? t('Prototype approved. Generate a Vite + React + Tailwind app.')
                  : t('Approve the prototype first.')}
              </p>
              <button
                type="button"
                className={`${BTN_SUCCESS} w-full`}
                disabled={busy || !session?.screens?.length || session.prototype_approved}
                onClick={() =>
                  void withBusy(async () => {
                    const next = await approveDesignPrototype(runId);
                    setSession(next);
                    setBusy(false);
                    return next;
                  })
                }
              >
                <Check size={14} /> {t('Approve')}
              </button>
              <button
                type="button"
                className={`${BTN_PRIMARY} w-full`}
                disabled={busy || !session?.prototype_approved}
                onClick={() =>
                  void withBusy(async () => {
                    const next = await generateDesignReact(runId);
                    setSession(next);
                    setBusy(false);
                    return next;
                  })
                }
              >
                {t('Generate UI code')}
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  className={`${BTN_SECONDARY} flex-1`}
                  disabled={busy || !session?.react_ready}
                  onClick={() =>
                    void withBusy(async () => {
                      const r = await startDesignPreview(runId);
                      setPreviewUrl(r.url);
                      setBusy(false);
                      return r;
                    })
                  }
                >
                  {t('Start preview')}
                </button>
                <button
                  type="button"
                  className={`${BTN_SECONDARY} flex-1`}
                  disabled={!previewUrl}
                  onClick={() =>
                    void withBusy(async () => {
                      await stopDesignPreview(runId);
                      setPreviewUrl(null);
                      setBusy(false);
                    })
                  }
                >
                  {t('Stop')}
                </button>
              </div>
              {previewUrl ? (
                <iframe title="preview" src={previewUrl} className="h-40 w-full rounded-xl border border-outline-variant/30" />
              ) : null}
              <button
                type="button"
                className={`${BTN_SUCCESS} w-full`}
                disabled={busy || !session?.react_ready || session.react_approved}
                onClick={() =>
                  void withBusy(async () => {
                    const next = await approveDesignReact(runId);
                    setSession(next);
                    setBusy(false);
                    return next;
                  })
                }
              >
                {t('Approve UI code')}
              </button>
              <button
                type="button"
                className={`${BTN_PRIMARY} w-full`}
                disabled={busy || !session?.react_approved}
                onClick={() =>
                  void withBusy(async () => {
                    const handoff = await sendDesignToCoding(runId);
                    onSendToCoding(handoff);
                    setBusy(false);
                    return handoff;
                  })
                }
              >
                {t('Send to Coding')}
              </button>
            </div>
          ) : null}

          {error ? (
            <div className="absolute left-1/2 top-4 z-20 -translate-x-1/2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
              {error}
            </div>
          ) : null}
        </>
      )}
    </>
  );
}

export const DesignWorkspace: React.FC<DesignWorkspaceProps> = (props) => {
  const { t } = useLanguage();
  if (!props.workspaceReady) {
    return (
      <div className="flex h-full items-center justify-center bg-surface font-sans text-sm text-neutral-500">
        {t('Authorize a workspace to use Design')}
      </div>
    );
  }

  return (
    <div className="relative h-full min-h-0 overflow-hidden bg-[#f7f7f8] font-sans" data-testid="design-workspace">
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          backgroundImage: 'radial-gradient(circle, #d4d4d8 1px, transparent 1px)',
          backgroundSize: '18px 18px',
        }}
      />
      <ReactFlowProvider>
        <DesignCanvasInner {...props} />
      </ReactFlowProvider>
    </div>
  );
};
