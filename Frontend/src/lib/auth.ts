/**
 * Session calls that go through the Next route handlers rather than straight to
 * Django, so the refresh token stays in an httpOnly cookie.
 */
import { apiFetch, type AuthUser } from "./api";

export interface SessionPayload {
  user: AuthUser | null;
  access: string | null;
  detail?: string;
}

function bff<T>(path: string, init: { method?: string; json?: unknown } = {}) {
  return apiFetch<T>(path, { baseUrl: "", ...init });
}

/**
 * Only one refresh-cookie operation may be in flight at a time.
 *
 * The backend rotates the refresh token on every use and blacklists the old one
 * immediately, so two overlapping calls would present the same token twice and
 * the loser would be signed out. That is not hypothetical: React Strict Mode
 * double-invokes the provider's mount effect in development, which fired two
 * session restores in the same millisecond and logged the user straight back
 * out on every page reload.
 *
 * Calls that share a key (the two restores above) share one request. Everything
 * else queues, and by the time it runs the browser already holds the rotated
 * cookie.
 *
 * This is per-tab. Two tabs reloading in the same instant can still race, and
 * the loser is asked to sign in again — the price of blacklisting on rotation.
 */
let pending: Promise<unknown> | null = null;
let pendingKey = "";

function gated<T>(run: () => Promise<T>, shareKey?: string): Promise<T> {
  if (shareKey && pending && pendingKey === shareKey) {
    return pending as Promise<T>;
  }

  // `then(run, run)` so a failed predecessor does not block the queue.
  const queued = (pending ?? Promise.resolve()).then(run, run);
  pending = queued;
  pendingKey = shareKey ?? "";

  const settle = () => {
    if (pending === queued) {
      pending = null;
      pendingKey = "";
    }
  };
  // Attached with both handlers so the bookkeeping never becomes an unhandled
  // rejection of its own; the caller still sees the real error.
  queued.then(settle, settle);

  return queued;
}

export const session = {
  /** Rebuild the session from the refresh cookie after a page load. */
  current: () =>
    gated(() => bff<SessionPayload>("/api/auth/session"), "current"),

  login: (email: string, password: string) =>
    gated(() =>
      bff<SessionPayload>("/api/auth/login", {
        method: "POST",
        json: { email, password },
      }),
    ),

  /** Confirm a registration code; the backend signs the user in on success. */
  verifyOtp: (email: string, code: string) =>
    gated(() =>
      bff<SessionPayload>("/api/auth/verify-otp", {
        method: "POST",
        json: { email, code },
      }),
    ),

  refresh: () =>
    gated(
      () => bff<SessionPayload>("/api/auth/refresh", { method: "POST" }),
      "refresh",
    ),

  logout: () =>
    gated(() => bff<{ detail: string }>("/api/auth/logout", { method: "POST" })),
};
