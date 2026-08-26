/**
 * Server-only helpers for talking to the Django backend and for the httpOnly
 * refresh-token cookie.
 *
 * Keeping the refresh token in a cookie that browser JavaScript cannot read
 * means an XSS bug cannot walk away with a long-lived session.
 */
import type { NextResponse } from "next/server";

/** Cookie holding the refresh token. Never readable from the browser. */
export const REFRESH_COOKIE = "bimaya_refresh";

/** Matches SIMPLE_JWT.REFRESH_TOKEN_LIFETIME on the backend (7 days). */
const REFRESH_MAX_AGE = 60 * 60 * 24 * 7;

/**
 * Base URL used from the server. Falls back to the public one so a single
 * env var is enough in development; set `BACKEND_API_URL` when the backend is
 * reachable at a different address from inside the deployment network.
 */
export function backendUrl(path: string): string {
  const base =
    process.env.BACKEND_API_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000/api/v1";
  return `${base}${path}`;
}

export interface BackendResult<T> {
  ok: boolean;
  status: number;
  data: T;
}

/** POST/GET the backend and always come back with a parsed body plus status. */
export async function backendFetch<T = unknown>(
  path: string,
  init: RequestInit & { json?: unknown; token?: string | null } = {},
): Promise<BackendResult<T>> {
  const { json, token, headers, ...rest } = init;

  const res = await fetch(backendUrl(path), {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(json !== undefined ? { body: JSON.stringify(json) } : {}),
    ...rest,
  });

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = (isJson ? await res.json().catch(() => null) : null) as T;

  return { ok: res.ok, status: res.status, data };
}

export function setRefreshCookie(response: NextResponse, token: string) {
  response.cookies.set({
    name: REFRESH_COOKIE,
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: REFRESH_MAX_AGE,
  });
}

export function clearRefreshCookie(response: NextResponse) {
  response.cookies.set({
    name: REFRESH_COOKIE,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
}
