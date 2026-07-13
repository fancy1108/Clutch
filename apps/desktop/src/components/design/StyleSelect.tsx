import { useRef, useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Check, ChevronDown, ChevronRight, FileText, Palette } from 'lucide-react';
import { useLanguage } from '../LanguageContext';

export type StyleOptionGroup = 'system' | 'custom';

export type StyleOption = {
  id: string;
  labelKey: string;
  descriptionKey: string;
  group: StyleOptionGroup;
  color?: string;
};

export type StyleSelectProps = {
  value: string;
  options: StyleOption[];
  onChange: (id: string) => void;
  disabled?: boolean;
  disabledTitle?: string;
  placeholderLabel?: string;
  onUploadClick?: () => void;
  onOpen?: () => void;
};

const PANEL_W = 288;
const PANEL_MAX_H = 420;
const PANEL_MIN_H = 160;
const GAP = 8;

function hexToRgb(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return null;
  let h = m[1];
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  const n = parseInt(h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function mix(c: [number, number, number], target: [number, number, number], t: number): string {
  const r = Math.round(c[0] + (target[0] - c[0]) * t);
  const g = Math.round(c[1] + (target[1] - c[1]) * t);
  const b = Math.round(c[2] + (target[2] - c[2]) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

function swatchBackground(color?: string): React.CSSProperties | undefined {
  if (!color) return undefined;
  const rgb = hexToRgb(color);
  if (!rgb) return { backgroundColor: color };
  const dark = mix(rgb, [0, 0, 0], 0.15);
  const light = mix(rgb, [255, 255, 255], 0.82);
  return { backgroundImage: `linear-gradient(135deg, ${dark}, ${light})` };
}

export function StyleSelect({
  value,
  options,
  onChange,
  disabled,
  disabledTitle,
  placeholderLabel,
  onUploadClick,
  onOpen,
}: StyleSelectProps) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [panelStyle, setPanelStyle] = useState<React.CSSProperties>({});
  const [systemExpanded, setSystemExpanded] = useState(true);
  const [customExpanded, setCustomExpanded] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback(() => {
    if (!btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const spaceAbove = rect.top - GAP;
    const spaceBelow = vh - rect.bottom - GAP;

    let top: number;
    let maxH: number;

    if (spaceAbove >= spaceBelow) {
      maxH = Math.min(spaceAbove, PANEL_MAX_H);
      maxH = Math.max(maxH, Math.min(PANEL_MIN_H, spaceAbove));
      top = Math.max(GAP, rect.top - GAP - maxH);
    } else {
      maxH = Math.min(spaceBelow, PANEL_MAX_H);
      maxH = Math.max(maxH, Math.min(PANEL_MIN_H, spaceBelow));
      top = rect.bottom + GAP;
    }

    top = Math.max(GAP, Math.min(top, vh - maxH - GAP));

    let left = rect.right - PANEL_W;
    left = Math.max(GAP, Math.min(left, vw - PANEL_W - GAP));

    setPanelStyle({ position: 'fixed', top, left, maxHeight: maxH, width: PANEL_W });
  }, []);

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      setOpen(false);
    };
    const handleKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeydown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeydown);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    const onScroll = () => updatePosition();
    const onResize = () => updatePosition();
    window.addEventListener('scroll', onScroll, true);
    window.addEventListener('resize', onResize);
    let ro: ResizeObserver | undefined;
    if (btnRef.current && typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(() => updatePosition());
      ro.observe(btnRef.current);
    }
    return () => {
      window.removeEventListener('scroll', onScroll, true);
      window.removeEventListener('resize', onResize);
      ro?.disconnect();
    };
  }, [open, updatePosition]);

  const selected = options.find((opt) => opt.id === value);
  const systemOptions = options.filter((opt) => opt.group === 'system');
  const customOptions = options.filter((opt) => opt.group === 'custom');

  const panel = open && !disabled ? (
    <div
      ref={panelRef}
      className="z-50 overflow-y-auto rounded-xl border border-neutral-200 bg-white shadow-lg"
      style={panelStyle}
    >
      {/* ── System ── */}
      <button
        type="button"
        className="sticky top-0 z-10 flex w-full items-center justify-between gap-2 bg-white px-3 py-2 pt-3 text-left hover:bg-neutral-50"
        onClick={() => setSystemExpanded((v) => !v)}
      >
        <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
          <ChevronRight
            size={12}
            className={`transition-transform duration-200 ${systemExpanded ? 'rotate-90' : ''}`}
          />
          {t('System')}
        </span>
        <span className="rounded-md bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-500 tabular-nums">
          {systemOptions.length}
        </span>
      </button>
      {systemExpanded ? (
        <div>
          {systemOptions.map((option) => {
            const active = value === option.id;
            return (
              <button
                key={option.id}
                type="button"
                className={`flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-neutral-50 transition-colors ${
                  active ? 'bg-neutral-50' : ''
                }`}
                onClick={() => {
                  onChange(option.id);
                  setOpen(false);
                }}
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-neutral-200 ${
                    option.color ? '' : 'bg-gradient-to-br from-neutral-800 via-neutral-500 to-neutral-200'
                  }`}
                  style={swatchBackground(option.color)}
                />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2 text-[12px] font-semibold text-neutral-900">
                    {t(option.labelKey)}
                    {active ? <Check size={14} className="shrink-0 text-sky-600" /> : null}
                  </span>
                  <span className="mt-0.5 block text-[11px] leading-snug text-neutral-500">
                    {t(option.descriptionKey)}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      ) : null}

      {/* ── Custom ── */}
      <div className="mx-3 border-t border-neutral-100" />

      {customExpanded ? (
        <div>
          {customOptions.length > 0 ? (
            customOptions.map((option) => {
              const active = value === option.id;
              return (
                <button
                  key={option.id}
                  type="button"
                  className={`flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-neutral-50 transition-colors ${
                    active ? 'bg-neutral-50' : ''
                  }`}
                  onClick={() => {
                    onChange(option.id);
                    setOpen(false);
                  }}
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-neutral-200 bg-neutral-100">
                    <FileText size={12} className="text-neutral-500" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2 text-[12px] font-semibold text-neutral-900">
                      {option.labelKey}
                      {active ? <Check size={14} className="shrink-0 text-sky-600" /> : null}
                    </span>
                    <span className="mt-0.5 block text-[11px] leading-snug text-neutral-500">
                      {option.descriptionKey}
                    </span>
                  </span>
                </button>
              );
            })
          ) : (
            <p className="px-3 py-3 text-[11px] leading-relaxed text-neutral-400">
              {t('Upload a DESIGN.md file to create your own style.')}
            </p>
          )}
        </div>
      ) : null}

      <button
        type="button"
        className="sticky bottom-0 z-10 flex w-full items-center justify-between gap-2 bg-white px-3 py-2 pb-3 text-left hover:bg-neutral-50"
        onClick={() => setCustomExpanded((v) => !v)}
      >
        <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-neutral-400">
          <ChevronRight
            size={12}
            className={`transition-transform duration-200 ${customExpanded ? 'rotate-90' : ''}`}
          />
          {t('Custom')}
        </span>
        <span className="flex items-center gap-2">
          <span className="rounded-md bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-500 tabular-nums">
            {customOptions.length}
          </span>

        </span>
      </button>
    </div>
  ) : null;

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={btnRef}
        type="button"
        className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold transition-colors ${
          disabled
            ? 'cursor-not-allowed text-neutral-300'
            : open
              ? 'bg-neutral-100 text-neutral-800'
              : 'text-neutral-600 hover:bg-neutral-100'
        }`}
        disabled={disabled}
        title={disabled ? (disabledTitle ?? '') : t('Design system')}
        aria-label={t('Design system')}
        onClick={() => {
          if (disabled) return;
          onOpen?.();
          setOpen((v) => !v);
        }}
      >
        <Palette size={14} />
        <span>{selected ? t(selected.labelKey) : (placeholderLabel ?? t('Clutch'))}</span>
        <ChevronDown
          size={12}
          className={`opacity-60 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {panel ? createPortal(panel, document.body) : null}
    </div>
  );
}