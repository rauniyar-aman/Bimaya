/**
 * Shared plumbing for the auth route handlers.
 */
import { NextResponse } from "next/server";
import type { AuthUser } from "@/lib/api";
import { setRefreshCookie } from "./backend";

export interface TokenPayload {
  access?: string;
  refresh?: string;
  user?: AuthUser;
  detail?: string;
}

/**
 * Hand the access token and user to the browser while the refresh token is
 * tucked into an httpOnly cookie.
 */
export function sessionResponse(payload: TokenPayload, status = 200) {
  const { refresh, ...visible } = payload;
  const response = NextResponse.json(visible, { status });
  if (refresh) setRefreshCookie(response, refresh);
  return response;
}

/**
 * Pass the caller's address along so the backend throttles per client rather
 * than per Next.js server.
 *
 * A browser can set `x-forwarded-for` itself, so set `DRF_NUM_PROXIES` in the
 * backend environment when deploying behind a reverse proxy — DRF then reads
 * the address the proxy appended instead of the whole chain.
 */
export function forwardedHeaders(request: Request): HeadersInit {
  const forwardedFor = request.headers.get("x-forwarded-for");
  return forwardedFor ? { "X-Forwarded-For": forwardedFor } : {};
}

export async function readJson(request: Request): Promise<unknown> {
  return request.json().catch(() => ({}));
}
