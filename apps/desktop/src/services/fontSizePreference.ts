export const DEFAULT_FONT_SIZE = 'default';

export const FONT_SIZE_OPTIONS = ['small', 'default', 'large', 'xlarge', 'xxlarge'] as const;

export type AppFontSize = (typeof FONT_SIZE_OPTIONS)[number];

export const FONT_SIZE_LABEL_KEYS: Record<AppFontSize, string> = {
  small: 'Small',
  default: 'Default',
  large: 'Large',
  xlarge: 'Extra Large',
  xxlarge: 'Super Large',
};

export function isAppFontSize(value: unknown): value is AppFontSize {
  return typeof value === 'string' && (FONT_SIZE_OPTIONS as readonly string[]).includes(value);
}
