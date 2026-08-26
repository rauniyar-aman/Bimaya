"use client";

/**
 * Development-only handoff of the one-time code between screens.
 *
 * There is no SMS gateway in development, so the API echoes the OTP back as
 * `dev_otp` (guarded by `OTP_RETURN_IN_RESPONSE`, which must be false in
 * production). Rather than making you dig through the server console, the code
 * is held in this tiny in-memory store and shown on the next screen.
 *
 * In memory on purpose: App Router navigations keep the same JavaScript
 * context, so the value survives the hop from register to verify, but a reload
 * clears it and nothing is ever written to disk.
 */
import { useSyncExternalStore } from "react";

let devCode: string | null = null;
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function rememberDevCode(code: string | null | undefined) {
  devCode = code ?? null;
  for (const listener of listeners) listener();
}

/** The code the API last echoed back, or `null` in production. */
export function useDevCode(): string | null {
  return useSyncExternalStore(
    subscribe,
    () => devCode,
    // Nothing to show during server rendering.
    () => null,
  );
}
