/** Fixed app chrome — Header height for main content offset. */
export const APP_HEADER_HEIGHT_PX = 64;

/** Fixed footer bar height (`h-8`). */
export const APP_FOOTER_HEIGHT_PX = 32;

/** Gap between input dock bottom edge and footer top. */
export const APP_INPUT_DOCK_FOOTER_GAP_PX = 16;

/** Fixed `bottom` offset for chat/terminal input docks (footer + gap). */
export const APP_INPUT_DOCK_BOTTOM_PX = APP_FOOTER_HEIGHT_PX + APP_INPUT_DOCK_FOOTER_GAP_PX;

/** Visible gap between last chat content and the fixed input dock top edge. */
export const CHAT_SCROLL_ABOVE_DOCK_GAP_PX = 32;

/** Main content / panels sit below fixed Header. */
export const CONTENT_TOP_WITH_BANNER = `${APP_HEADER_HEIGHT_PX}px`;

export const SIDEBAR_EXPANDED_WIDTH_PX = 260;
export const SIDEBAR_COLLAPSED_WIDTH_PX = 56;

/** Workspace chrome row — Chat/Terminal mode toggle offset below Header. */
export const WORKSPACE_CHROME_ROW_TOP_PX = 20;

/** Header breadcrumb (workspace / flow) inset from main content left edge. */
export const HEADER_BREADCRUMB_LEFT_PADDING_PX = 20;

/** Panel edge toggles — vertically centered in main content below Header. */
export const CHROME_PANEL_TOGGLE_HALF_PX = 12;
/** Viewport-fixed left toggle — centers in content column below header. */
export const CHROME_PANEL_TOGGLE_TOP_CSS = `calc(${APP_HEADER_HEIGHT_PX}px + (100vh - ${APP_HEADER_HEIGHT_PX}px) / 2 - ${CHROME_PANEL_TOGGLE_HALF_PX}px)`;
/** Absolute top within RightPanel aside (aside starts at CONTENT_TOP_WITH_BANNER). */
export const CHROME_PANEL_TOGGLE_TOP_IN_PANEL_CSS = `calc(50% - ${CHROME_PANEL_TOGGLE_HALF_PX}px)`;
