import type { ILink, ILinkProvider, Terminal } from '@xterm/xterm';
import { findPathCandidates, stripPathPunctuation } from '../../services/workspacePathLinks';

type OpenPathHandler = (path: string) => void;

/** xterm link provider: workspace paths / filenames → preview via resolve. */
export function createWorkspacePathLinkProvider(
  term: Terminal,
  onOpenPath: OpenPathHandler,
): ILinkProvider {
  return {
    provideLinks(y, callback) {
      try {
        const line = term.buffer.active.getLine(y - 1);
        if (!line) {
          callback(undefined);
          return;
        }
        let text = '';
        for (let i = 0; i < line.length; i++) {
          text += line.getCell(i)?.getChars() ?? '';
        }
        const candidates = findPathCandidates(text);
        if (candidates.length === 0) {
          callback(undefined);
          return;
        }
        const links: ILink[] = candidates.map((c) => {
          const cleaned = stripPathPunctuation(c.raw);
          return {
            range: {
              start: { x: c.start + 1, y },
              end: { x: c.end, y },
            },
            text: cleaned,
            activate: () => {
              try {
                onOpenPath(cleaned);
              } catch {
                // Never let link clicks crash the terminal host.
              }
            },
          };
        });
        callback(links);
      } catch {
        callback(undefined);
      }
    },
  };
}
