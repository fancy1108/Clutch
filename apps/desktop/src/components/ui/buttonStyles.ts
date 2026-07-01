/** Shared compact button sizes — align with UI_UX_GUIDELINES §4.2 */

export const BTN_FOCUS =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-900/20 focus-visible:ring-offset-1';

export const BTN_BASE =
  `inline-flex items-center justify-center gap-1 font-semibold transition-all duration-200 cursor-pointer whitespace-nowrap disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] ${BTN_FOCUS}`;

export const BTN_SM = `${BTN_BASE} px-2.5 py-1 text-[11px] rounded-md`;
export const BTN_MD = `${BTN_BASE} px-3 py-1.5 text-[11px] rounded-lg`;

export const BTN_PRIMARY = `${BTN_MD} bg-neutral-900 hover:bg-black text-white border border-neutral-900 shadow-sm`;
export const BTN_PRIMARY_SM = `${BTN_SM} bg-neutral-900 hover:bg-black text-white border border-neutral-900 shadow-sm`;
export const BTN_SECONDARY = `${BTN_MD} bg-neutral-50 hover:bg-neutral-100 text-neutral-700 hover:text-neutral-950 border border-neutral-200/60`;
export const BTN_GHOST = `${BTN_MD} text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 border border-neutral-200/60`;
export const BTN_GHOST_SM = `${BTN_SM} text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 border border-neutral-200/60`;

export const BTN_SUCCESS_SM = `${BTN_SM} bg-emerald-50 hover:bg-emerald-600 border border-emerald-200 text-emerald-800 hover:text-white uppercase tracking-wide`;
export const BTN_DANGER_SM = `${BTN_SM} bg-rose-50 hover:bg-rose-600 border border-rose-200 text-rose-800 hover:text-white uppercase tracking-wide`;

export const BTN_ICON = `${BTN_BASE} p-1.5 rounded-md text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high`;
export const BTN_ICON_SM = `${BTN_BASE} p-0.5 rounded text-on-surface-variant hover:text-primary opacity-60 hover:opacity-100`;
