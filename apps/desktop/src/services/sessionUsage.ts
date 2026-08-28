/** Format Overview session token meters (Q-USAGE-1). */

export function formatTokenMeter(n: number, estimated: boolean): string {
  if (!Number.isFinite(n) || n <= 0) return '—';
  const body = Math.round(n).toLocaleString('en-US');
  return estimated ? `~${body}` : body;
}

export function formatStepMeter(steps: number, maxSteps?: number): string {
  if (!Number.isFinite(steps) || steps < 0) return '—';
  const used = Math.round(steps);
  if (maxSteps && maxSteps > 0) return `${used}/${Math.round(maxSteps)}`;
  return used > 0 ? String(used) : '—';
}

export function inputOutputPercents(
  input: number,
  output: number,
): { inPct: number; outPct: number } {
  const total = Math.max(0, input) + Math.max(0, output);
  if (total <= 0) return { inPct: 50, outPct: 50 };
  const inPct = Math.round((Math.max(0, input) / total) * 100);
  return { inPct, outPct: 100 - inPct };
}
