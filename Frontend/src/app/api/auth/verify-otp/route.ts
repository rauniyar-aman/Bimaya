/**
 * POST /api/auth/verify-otp — confirm a registration code.
 *
 * A successful verification signs the user straight in, so this behaves like
 * login: refresh token to the cookie, access token to the browser.
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

  const { ok, status, data } = await backendFetch<TokenPayload>(
    "/auth/verify-otp/",
    { method: "POST", json: body, headers: forwardedHeaders(request) },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? { detail: "Could not verify that code." },
      { status },
    );
  }
  return sessionResponse(data);
}
