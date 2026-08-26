/**
 * POST /api/auth/login — exchange email + password for a session.
 *
 * The refresh token is stored as an httpOnly cookie; only the short-lived
 * access token is handed back to the browser.
 */
import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/server/backend";
import {
  forwardedHeaders,
  readJson,
  sessionResponse,
  type TokenPayload,
} from "@/lib/server/session";

export async function POST(request: Request) {
  const body = await readJson(request);

  const { ok, status, data } = await backendFetch<TokenPayload>("/auth/login/", {
    method: "POST",
    json: body,
    headers: forwardedHeaders(request),
  });

  if (!ok) {
    return NextResponse.json(data ?? { detail: "Could not sign in." }, { status });
  }
  return sessionResponse(data);
}
