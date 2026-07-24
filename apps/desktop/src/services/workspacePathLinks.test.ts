import { describe, expect, it } from 'vitest';
import {
  extractImagePathsFromDispatch,
  findPathCandidates,
  isImageWorkspacePath,
  isLargePreviewContent,
  stripPathPunctuation,
} from './workspacePathLinks';

describe('workspacePathLinks', () => {
  it('strips trailing punctuation', () => {
    expect(stripPathPunctuation('./foo.ts,')).toBe('foo.ts');
    expect(stripPathPunctuation('src/a.tsx)')).toBe('src/a.tsx');
  });

  it('finds relative paths and bare filenames', () => {
    const line = 'Edited src/components/Button.tsx and also Button.tsx,';
    const hits = findPathCandidates(line).map((h) => stripPathPunctuation(h.raw));
    expect(hits).toContain('src/components/Button.tsx');
    expect(hits.some((h) => h === 'Button.tsx' || h.endsWith('Button.tsx'))).toBe(true);
  });

  it('detects large preview content', () => {
    expect(isLargePreviewContent('short')).toBe(false);
    expect(isLargePreviewContent(`${'x'.repeat(500 * 1024)}`)).toBe(true);
  });

  it('extracts attachment images from dispatch prompt', () => {
    const prompt =
      '[Image analysis for .clutch/attachments/1784877032089.png]\n[Attached image]\n[file: .clutch/attachments/1784877032089.png]\n@.clutch/attachments/1784877032089.png';
    expect(isImageWorkspacePath('.clutch/attachments/a.png')).toBe(true);
    expect(extractImagePathsFromDispatch(prompt, [])).toEqual([
      '.clutch/attachments/1784877032089.png',
    ]);
    expect(
      extractImagePathsFromDispatch('hello', ['.clutch/attachments/x.jpg', 'notes.md']),
    ).toEqual(['.clutch/attachments/x.jpg']);
  });
});
