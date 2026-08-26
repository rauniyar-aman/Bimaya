/**
 * POST /api/auth/refresh — mint a new access token from the refresh cookie.
 *
 * The backend rotates refresh tokens and blacklists the previous one, so the
 * cookie is replaced on every call.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
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

export async function POST(request: Request) {
  const refresh = (await cookies()).get(REFRESH_COOKIE)?.value;

  if (!refresh) {
    return NextResponse.json(
      { detail: "You are not signed in.", code: "no_session" },
      { status: 401 },
    );
  }

  const { ok, status, data } = await backendFetch<TokenPayload>("/auth/refresh/", {
    method: "POST",
    json: { refresh },
    headers: forwardedHeaders(request),
  });

  if (!ok) {
    // The cookie is stale (expired or blacklisted) — drop it so the client
    // stops trying and shows the signed-out state.
    const response = NextResponse.json(
      data ?? { detail: "Your session has expired.", code: "session_expired" },
      { status },
    );
    clearRefreshCookie(response);
    return response;
  }

  return sessionResponse(data);
}
