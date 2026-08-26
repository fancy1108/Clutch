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
});
