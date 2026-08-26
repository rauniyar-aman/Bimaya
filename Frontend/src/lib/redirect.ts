/**
 * Sanitise a `?next=` destination.
 *
 * Anything that is not a plain in-app path is dropped, so a crafted link cannot
 * bounce a freshly signed-in user off to another site (open redirect).
 */
export const DEFAULT_REDIRECT = "/dashboard";

export function safeNext(
  value: string | null | undefined,
  fallback: string = DEFAULT_REDIRECT,
): string {
  if (!value) return fallback;
  // Must be root-relative, and not "//host" or "/\host" which browsers read as
  // protocol-relative URLs.
  if (!value.startsWith("/") || /^\/[/\\]/.test(value)) return fallback;
  return value;
}
