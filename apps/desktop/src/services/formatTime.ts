/** Parse dispatch log timestamps (ISO 8601 or legacy UTC HH:MM from orchestrator). */
export function parseDispatchTimestamp(value: string): Date | null {
  const trimmed = value.trim();
  if (!trimmed) return null;

  const legacyUtc = /^(\d{2}):(\d{2})$/.exec(trimmed);
  if (legacyUtc) {
    const hour = Number(legacyUtc[1]);
    const minute = Number(legacyUtc[2]);
    if (hour > 23 || minute > 59) return null;
    const now = new Date();
    return new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), hour, minute),
    );
  }

  const parsed = Date.parse(trimmed);
  if (Number.isNaN(parsed)) return null;
  return new Date(parsed);
}

/** Format dispatch time in the user's local timezone (e.g. China UTC+8). */
export function formatDispatchTime(value: string): string {
  const date = parseDispatchTimestamp(value);
  if (!date) return value;
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}
