/** Fixed app chrome — Header height + optional UpdateBanner offset via CSS variable. */
export const APP_HEADER_HEIGHT_PX = 64;

export const UPDATE_BANNER_HEIGHT_VAR = '--clutch-update-banner-h';

/** Main content / panels sit below Header + UpdateBanner when visible. */
export const CONTENT_TOP_WITH_BANNER = `calc(${APP_HEADER_HEIGHT_PX}px + var(${UPDATE_BANNER_HEIGHT_VAR}, 0px))`;
