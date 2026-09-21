import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import React from 'react';
import { UncommittedChangesList } from './UncommittedChangesList';
import type { UncommittedFile } from '../types';

const t = (key: string) => key;

function file(name: string, status: UncommittedFile['status'] = 'M'): UncommittedFile {
  return { name, status, diffs: [] };
}

describe('UncommittedChangesList', () => {
  it('renders empty state when no files', () => {
    const out = renderToStaticMarkup(
      <UncommittedChangesList
        files={[]}
        selectedFile={null}
        onSelect={() => {}}
        t={t}
      />,
    );
    expect(out).toContain('No uncommitted changes');
    expect(out).not.toContain('data-testid="uncommitted-changes-list"');
  });

  it('renders flat list without filter when below threshold', () => {
    const files = [file('a.md'), file('b.md'), file('c.md')];
    const out = renderToStaticMarkup(
      <UncommittedChangesList
        files={files}
        selectedFile={null}
        onSelect={() => {}}
        t={t}
      />,
    );
    // No filter input (only 3 files < 20 threshold)
    expect(out).not.toContain('data-testid="uncommitted-changes-filter');
    // All files visible (small list, all groups open by default)
    expect(out).toContain('a.md');
    expect(out).toContain('b.md');
    expect(out).toContain('c.md');
  });

  it('groups files by top-level directory', () => {
    const files = [
      file('src/a.ts'),
      file('src/b.ts'),
      file('docs/readme.md'),
      file('root.txt'),
    ];
    const out = renderToStaticMarkup(
      <UncommittedChangesList
        files={files}
        selectedFile={null}
        onSelect={() => {}}
        t={t}
      />,
    );
    // Groups present
    expect(out).toContain('data-testid="uncommitted-group-src"');
    expect(out).toContain('data-testid="uncommitted-group-docs"');
    expect(out).toContain('data-testid="uncommitted-group-."');
    // Short names rendered (basename only)
    expect(out).toContain('a.ts');
    expect(out).toContain('b.ts');
    expect(out).toContain('readme.md');
    expect(out).toContain('root.txt');
  });

  it('shows filter input when files exceed threshold', () => {
    const files = Array.from({ length: 25 }, (_, i) => file(`file-${i}.md`));
    const out = renderToStaticMarkup(
      <UncommittedChangesList
        files={files}
        selectedFile={null}
        onSelect={() => {}}
        t={t}
      />,
    );
    expect(out).toContain('data-testid="uncommitted-changes-filter"');
    expect(out).toContain('Filter files...');
  });

  it('collapses all groups by default when total exceeds collapse threshold', () => {
    // 60 files in 3 dirs → exceeds COLLAPSE_ALL_THRESHOLD (50)
    const files = [
      ...Array.from({ length: 25 }, (_, i) => file(`src/f${i}.ts`)),
      ...Array.from({ length: 20 }, (_, i) => file(`docs/f${i}.md`)),
      ...Array.from({ length: 15 }, (_, i) => file(`root${i}.txt`)),
    ];
    const out = renderToStaticMarkup(
      <UncommittedChangesList
        files={files}
        selectedFile={null}
        onSelect={() => {}}
        t={t}
      />,
    );
    // Group headers present
    expect(out).toContain('data-testid="uncommitted-group-src"');
    expect(out).toContain('data-testid="uncommitted-group-docs"');
    expect(out).toContain('data-testid="uncommitted-group-."');
    // But file contents hidden (groups collapsed)
    expect(out).not.toContain('f0.ts');
    expect(out).not.toContain('f0.md');
    expect(out).not.toContain('root0.txt');
    // Counts shown on group headers
    expect(out).toContain('25');
    expect(out).toContain('20');
    expect(out).toContain('15');
  });

  it('marks selected file as active', () => {
    const files = [file('a.md'), file('b.md')];
    const out = renderToStaticMarkup(
      <UncommittedChangesList
        files={files}
        selectedFile={'b.md'}
        onSelect={() => {}}
        t={t}
      />,
    );
    // Active file gets bold styling (border class present on its row)
    expect(out).toContain('border-outline-variant/30');
  });
});
