import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import React from 'react';
import { FilesChangedChips } from './FilesChangedChips';

const t = (key: string) => key;

describe('FilesChangedChips', () => {
  it('renders nothing for empty paths', () => {
    const out = renderToStaticMarkup(
      <FilesChangedChips paths={[]} label="Changed files" t={t} />,
    );
    expect(out).toBe('');
  });

  it('renders all chips inline when count is below threshold', () => {
    const paths = ['a.md', 'b.md', 'c.md'];
    const out = renderToStaticMarkup(
      <FilesChangedChips paths={paths} label="Changed files" t={t} />,
    );
    // 3 chips + label, no toggle button
    expect(out).toContain('a.md');
    expect(out).toContain('b.md');
    expect(out).toContain('c.md');
    expect(out).not.toContain('Show all');
    expect(out).not.toContain('data-testid="files-changed-chips-toggle"');
  });

  it('collapses when count exceeds threshold and shows total + toggle', () => {
    const paths = Array.from({ length: 20 }, (_, i) => `file-${i}.md`);
    const out = renderToStaticMarkup(
      <FilesChangedChips paths={paths} label="Changed files" t={t} />,
    );
    // Total count shown
    expect(out).toContain('(20)');
    // Toggle button present (collapsed by default)
    expect(out).toContain('data-testid="files-changed-chips-toggle"');
    // {n} is replaced with hidden count (20 - 8 = 12)
    expect(out).toContain('Show all (12)');
    // Only preview chips rendered (file-0 .. file-7), file-8+ hidden
    expect(out).toContain('file-0.md');
    expect(out).toContain('file-7.md');
    expect(out).not.toContain('file-8.md');
    expect(out).not.toContain('file-19.md');
    // Expanded container not rendered when collapsed
    expect(out).not.toContain('data-testid="files-changed-chips-expanded"');
  });

  it('deduplicates paths before counting', () => {
    const paths = ['a.md', 'a.md', 'b.md'];
    const out = renderToStaticMarkup(
      <FilesChangedChips paths={paths} label="Changed files" t={t} />,
    );
    // 2 unique files, below threshold → no collapse
    expect(out).not.toContain('data-testid="files-changed-chips-toggle"');
  });
});
