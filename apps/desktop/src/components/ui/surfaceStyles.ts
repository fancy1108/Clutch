/** Shared surfaces — align with UI_UX_GUIDELINES §4.1–§4.4 */

export const CARD =
  'p-4 bg-surface-container-low rounded-2xl border border-outline-variant/30 shadow-sm';

export const CARD_SUBTLE =
  'p-4 bg-neutral-50/50 border border-neutral-200/60 rounded-xl';

export const CARD_INSET =
  'p-3 border border-outline-variant/30 rounded-xl bg-surface-container-low/40';

export const ALERT_ERROR =
  'text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2';

export const ALERT_WARNING =
  'text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2';

export const ALERT_SUCCESS =
  'text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2';

export const ALERT_INFO =
  'text-xs text-neutral-700 bg-neutral-50 border border-neutral-200 rounded-lg px-3 py-2';

/** Full-width app banner below Header — UI_UX_GUIDELINES §4.4 info feedback */
export const BANNER_INFO =
  'flex items-center justify-between gap-4 px-4 py-2.5 bg-surface-container-low/95 backdrop-blur-md border-b border-outline-variant/30 text-on-surface shadow-sm';

export const BANNER_PROGRESS_TRACK =
  'h-1.5 max-w-[220px] flex-1 rounded-full bg-outline-variant/60 overflow-hidden';

export const BANNER_PROGRESS_FILL = 'h-full rounded-full bg-primary origin-left';

export const BADGE_SUCCESS =
  'text-[9px] uppercase font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded';

export const BADGE_NEUTRAL =
  'text-[9px] uppercase font-bold text-neutral-700 bg-neutral-100 px-1.5 py-0.5 rounded';

export const BADGE_PRIMARY =
  'text-[9px] uppercase font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded';

export const INPUT_FIELD =
  'w-full text-xs border border-outline bg-surface rounded-lg px-3 py-2 text-on-surface focus:outline-none focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900/20 transition-all';

export const SECTION_EYEBROW =
  'font-bold text-[10px] uppercase tracking-wider text-on-surface-variant';

export const EMPTY_STATE =
  'p-6 border border-dashed border-outline-variant/50 rounded-xl text-center space-y-2 text-on-surface-variant';
