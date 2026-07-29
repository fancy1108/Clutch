import { describe, expect, it } from 'vitest';
import { absoluteWorkspacePath, isHtmlWorkspacePath } from './openInSystem';

describe('openInSystem helpers', () => {
  it('detects html paths', () => {
    expect(isHtmlWorkspacePath('ancient_emperors.html')).toBe(true);
    expect(isHtmlWorkspacePath('docs/index.HTM')).toBe(true);
    expect(isHtmlWorkspacePath('readme.md')).toBe(false);
  });

  it('joins workspace root and relative path', () => {
    expect(absoluteWorkspacePath('/Users/me/proj', 'ancient_emperors.html')).toBe(
      '/Users/me/proj/ancient_emperors.html',
    );
    expect(absoluteWorkspacePath('C:\\ws', 'a\\b.html')).toBe('C:\\ws\\a\\b.html');
  });
});
