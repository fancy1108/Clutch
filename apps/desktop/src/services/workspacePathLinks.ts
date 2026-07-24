/** Shared path / filename detection for Chat + Terminal preview links. */

export const SOURCE_FILE_EXT =
  /\.(?:ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|swift|md|json|ya?ml|toml|css|scss|html|vue|svelte|sh|bash|zsh|sql|graphql|proto|rb|php|cs|cpp|c|h|hpp|txt|env|lock|svg|png|jpe?g|gif|webp)$/i;

/** Strip trailing punctuation / quotes commonly glued to paths in CLI output. */
export function stripPathPunctuation(raw: string): string {
  let text = raw.trim().replace(/^[`'"]+|[`'"]+$/g, '');
  text = text.replace(/[,.;:)\]}>]+$/g, '');
  if (text.startsWith('./')) text = text.slice(2);
  return text;
}

/**
 * Find path-like tokens in a line for linkification.
 * Returns ranges in the original string (before strip) when possible.
 */
export function findPathCandidates(line: string): Array<{ raw: string; start: number; end: number }> {
  const results: Array<{ raw: string; start: number; end: number }> = [];
  // Absolute, relative with slash, or bare filename with extension
  const re =
    /(?:\/[\w.@+-]+(?:\/[\w.@+-]+)+\/?|\.{0,2}\/[\w.@+/-]+|[\w.@+-]+\/[\w.@+/-]+|(?:[\w.@+-]+)?\.(?:ts|tsx|js|jsx|mjs|cjs|py|go|rs|java|kt|swift|md|json|ya?ml|toml|css|scss|html|vue|svelte|sh|bash|zsh|sql|graphql|proto|rb|php|cs|cpp|c|h|hpp|txt|env|lock|svg))\b/gi;
  let match: RegExpExecArray | null;
  while ((match = re.exec(line)) !== null) {
    const raw = match[0];
    if (/^https?:\/\//i.test(raw)) continue;
    const cleaned = stripPathPunctuation(raw);
    if (!cleaned || cleaned.length < 3) continue;
    // Require slash or known extension to avoid package names
    if (!cleaned.includes('/') && !SOURCE_FILE_EXT.test(cleaned)) continue;
    results.push({ raw, start: match.index, end: match.index + raw.length });
  }
  return results;
}

export const FILE_MARKER_RE = /\[file:\s*([^\]]+)\]/gi;
export const AT_PATH_RE = /@((?:\.\/)?[\w.@+/-]+\.[A-Za-z0-9]+)/g;
export const IMAGE_PATH_EXT_RE = /\.(?:png|jpe?g|gif|webp|bmp|svg)$/i;
const IMAGE_ANALYSIS_PATH_RE = /\[Image analysis for\s+([^\]]+)\]/gi;

export function isImageWorkspacePath(path: string): boolean {
  return IMAGE_PATH_EXT_RE.test(stripPathPunctuation(path));
}

/** Collect unique image paths from dispatch prompt + file_refs for thumbnail preview. */
export function extractImagePathsFromDispatch(text: string, fileRefs?: string[] | null): string[] {
  const ordered: string[] = [];
  const seen = new Set<string>();
  const push = (raw: string) => {
    const cleaned = stripPathPunctuation(raw);
    if (!cleaned || !isImageWorkspacePath(cleaned) || seen.has(cleaned)) return;
    seen.add(cleaned);
    ordered.push(cleaned);
  };
  for (const ref of fileRefs ?? []) push(ref);
  const fileRe = new RegExp(FILE_MARKER_RE.source, 'gi');
  let match: RegExpExecArray | null;
  while ((match = fileRe.exec(text)) !== null) push(match[1]);
  const atRe = new RegExp(AT_PATH_RE.source, 'g');
  while ((match = atRe.exec(text)) !== null) push(match[1]);
  const analysisRe = new RegExp(IMAGE_ANALYSIS_PATH_RE.source, 'gi');
  while ((match = analysisRe.exec(text)) !== null) push(match[1]);
  return ordered;
}

export const LARGE_PREVIEW_LINE_THRESHOLD = 2000;
export const LARGE_PREVIEW_BYTE_THRESHOLD = 500 * 1024;
export const CODE_BLOCK_COLLAPSE_LINES = 40;

export function isLargePreviewContent(content: string): boolean {
  if (content.length >= LARGE_PREVIEW_BYTE_THRESHOLD) return true;
  let lines = 1;
  for (let i = 0; i < content.length; i++) {
    if (content.charCodeAt(i) === 10) {
      lines += 1;
      if (lines >= LARGE_PREVIEW_LINE_THRESHOLD) return true;
    }
  }
  return false;
}
