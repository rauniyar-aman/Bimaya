/**
 * Display helpers for the ISO date strings the API returns (e.g. "2026-09-06").
 *
 * Kept separate from `format.ts` (money / terms) so the money helpers stay free
 * of date concerns. Every helper tolerates null / unparseable input.
 */

/** "6 September 2026" — long form, or "—" when the value is missing or invalid. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** "just now" / "5m ago" / "3h ago" / "2d ago", falling back to a date. */
export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (seconds < 45) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return formatDate(value);
}

/**
 * Whole days from today until `value` (negative once it is in the past).
 * Returns `null` when the value is missing or unparseable.
 */
export function daysUntil(value: string | null | undefined): number | null {
  if (!value) return null;
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) return null;

  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const startOfTarget = new Date(
    target.getFullYear(),
    target.getMonth(),
    target.getDate(),
  );

  const msPerDay = 24 * 60 * 60 * 1000;
  return Math.round((startOfTarget.getTime() - startOfToday.getTime()) / msPerDay);
}
