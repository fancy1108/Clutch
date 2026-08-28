import { describe, expect, it } from 'vitest';
import { isMappedLegacyIcon } from './LegacyIcon';

/** Composer + menu — unknown names render as an empty circle. */
const PLUS_MENU_ICONS = [
  'attach_file',
  'folder_open',
  'history',
  'sparkles',
  'clipboard_list',
  'undo',
  'hub',
  'bell',
  'inbox',
  'bug',
  'calendar_clock',
  'folder-git',
];

describe('LegacyIcon map', () => {
  it('maps every + menu icon so none fall back to Circle', () => {
    for (const name of PLUS_MENU_ICONS) {
      expect(isMappedLegacyIcon(name), name).toBe(true);
    }
  });
});
