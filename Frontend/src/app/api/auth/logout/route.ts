/**
 * POST /api/auth/logout — end the session everywhere.
 *
 * The refresh cookie is exchanged for a short-lived access token, which is used
 * to blacklist the refresh token on the backend before the cookie is cleared.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import {
  REFRESH_COOKIE,
  backendFetch,
  clearRefreshCookie,
} from "@/lib/server/backend";
import { forwardedHeaders, type TokenPayload } from "@/lib/server/session";

export async function POST(request: Request) {
  const refresh = (await cookies()).get(REFRESH_COOKIE)?.value;
  const response = NextResponse.json({ detail: "Signed out." });
  clearRefreshCookie(response);

  if (!refresh) return response;

  const rotated = await backendFetch<TokenPayload>("/auth/refresh/", {
    method: "POST",
    json: { refresh },
    headers: forwardedHeaders(request),
  });

  if (rotated.ok && rotated.data?.access && rotated.data?.refresh) {
    await backendFetch("/auth/logout/", {
      method: "POST",
      token: rotated.data.access,
      json: { refresh: rotated.data.refresh },
      headers: forwardedHeaders(request),
    });
  }

  // Either way the cookie is gone, so the browser session is over.
  return response;
}
