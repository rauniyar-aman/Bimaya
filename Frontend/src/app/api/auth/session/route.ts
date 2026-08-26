/**
 * GET /api/auth/session — rebuild the session after a page load.
 *
 * The browser keeps the access token in memory only, so on every fresh load we
 * spend the refresh cookie for a new access token and fetch the user. Returns
 * `{ user: null }` when nobody is signed in — that is a normal state, not an
 * error.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import type { AuthUser } from "@/lib/api";
import {
  REFRESH_COOKIE,
  backendFetch,
  clearRefreshCookie,
} from "@/lib/server/backend";
import {
  forwardedHeaders,
  sessionResponse,
  type TokenPayload,
} from "@/lib/server/session";

const signedOut = () => NextResponse.json({ user: null, access: null });

export async function GET(request: Request) {
  const refresh = (await cookies()).get(REFRESH_COOKIE)?.value;
  if (!refresh) return signedOut();

  const rotated = await backendFetch<TokenPayload>("/auth/refresh/", {
    method: "POST",
    json: { refresh },
    headers: forwardedHeaders(request),
  });

  if (!rotated.ok || !rotated.data?.access) {
    const response = signedOut();
    clearRefreshCookie(response);
    return response;
  }

  const me = await backendFetch<AuthUser>("/auth/me/", {
    token: rotated.data.access,
    headers: forwardedHeaders(request),
  });

  if (!me.ok) {
    const response = signedOut();
    clearRefreshCookie(response);
    return response;
  }

  return sessionResponse({
    access: rotated.data.access,
    refresh: rotated.data.refresh,
    user: me.data,
  });
}
