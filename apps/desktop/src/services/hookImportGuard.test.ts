import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const SRC = join(dirname(fileURLToPath(import.meta.url)), '..');

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return walk(path);
    return /\.(tsx|ts)$/.test(name) && !name.includes('.test.') ? [path] : [];
  });
}

describe('hook import guard', () => {
  it('files that call useLanguage or useHostOs import them', () => {
    const missing: string[] = [];
    for (const file of walk(SRC)) {
      const src = readFileSync(file, 'utf8');
      for (const hook of ['useLanguage', 'useHostOs'] as const) {
        if (!new RegExp(`\\b${hook}\\s*\\(`).test(src)) continue;
        if (new RegExp(`(export\\s+(function|const)\\s+${hook}\\b|function\\s+${hook}\\s*\\()`).test(src)) {
          continue;
        }
        const imported = new RegExp(
          `import\\s*\\{[^}]*\\b${hook}\\b[^}]*\\}\\s*from\\s*['"][^'"]+['"]`,
        ).test(src);
        if (!imported) missing.push(`${file} ${hook}`);
      }
    }
    expect(missing).toEqual([]);
  });

  it('FM-10 has Assigned Agent select and no Node engine override', () => {
    const src = readFileSync(join(SRC, 'components/WorkflowOrchestration.tsx'), 'utf8');
    expect(src).toContain('data-testid="node-agent-select"');
    expect(src).not.toContain('data-testid="node-tool-select"');
    expect(src).not.toContain("t('Node engine')");
  });

  it('FM-18 wires validation failure testids on Chat and Overview', () => {
    const feed = readFileSync(join(SRC, 'components/ChatFeed.tsx'), 'utf8');
    const panel = readFileSync(join(SRC, 'components/RightPanel.tsx'), 'utf8');
    expect(feed).toContain('validation-failure-chat');
    expect(panel).toContain('data-testid="validation-failure-strip"');
  });
});
