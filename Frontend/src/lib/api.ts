/**
 * Typed client for the Bimaya REST API.
 *
 * The base URL points at the Django backend (`/api/v1`). Requests include
 * credentials so the httpOnly refresh-token cookie flows where it is needed.
 *
 * Endpoints that mint or spend tokens (login, verify, refresh, logout) go
 * through the Next route handlers in `src/app/api/auth` instead — see
 * `src/lib/auth.ts` — so the refresh token never reaches browser JavaScript.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly data: unknown;

  constructor(message: string, status: number, data: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export interface ApiFetchOptions extends RequestInit {
  /** Omit cookies for this request (defaults to including them). */
  noCredentials?: boolean;
  /** Bearer token to authenticate the request with. */
  token?: string | null;
  /** Body to send as JSON — serialised and content-typed automatically. */
  json?: unknown;
  /** Override the API base — pass `""` to call a same-origin Next route. */
  baseUrl?: string;
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const {
    noCredentials,
    headers,
    body,
    token,
    json,
    baseUrl = API_BASE_URL,
    ...rest
  } = options;
  const url = path.startsWith("http") ? path : `${baseUrl}${path}`;
  const payload = json !== undefined ? JSON.stringify(json) : body;

  const res = await fetch(url, {
    credentials: noCredentials ? "omit" : "include",
    headers: {
      Accept: "application/json",
      ...(payload ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(payload !== undefined ? { body: payload } : {}),
    ...rest,
  });

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json().catch(() => null) : await res.text();

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(detail || "Request failed", res.status, data);
  }

  return data as T;
}

/* -------------------------------------------------------------------------- */
/* Shared shapes                                                              */
/* -------------------------------------------------------------------------- */

export type UserRole = "CUSTOMER" | "PROVIDER" | "ADMIN";

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: UserRole;
  is_verified: boolean;
  date_joined: string;
}

/** The uniform error envelope returned by the API. */
export interface ApiErrorBody {
  detail: string;
  code?: string;
  errors?: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface RegisterPayload {
  email: string;
  full_name: string;
  phone: string;
  role: Exclude<UserRole, "ADMIN">;
  password: string;
  confirm_password: string;
}

export interface MessageResponse {
  detail: string;
  /** Development only: the OTP, since there is no SMS gateway locally. */
  dev_otp?: string;
}

export interface RegisterResponse extends MessageResponse {
  email: string;
}

/* -------------------------------------------------------------------------- */
/* Error helpers                                                              */
/* -------------------------------------------------------------------------- */

function errorBody(error: unknown): ApiErrorBody | null {
  if (!(error instanceof ApiError)) return null;
  const data = error.data;
  return data && typeof data === "object" ? (data as ApiErrorBody) : null;
}

/** Flatten `errors` into one message per field, ready for form display. */
export function fieldErrors(error: unknown): Record<string, string> {
  const errors = errorBody(error)?.errors;
  if (!errors) return {};

  const flat: Record<string, string> = {};
  for (const [field, value] of Object.entries(errors)) {
    const message = Array.isArray(value) ? value[0] : value;
    if (message != null) flat[field] = String(message);
  }
  return flat;
}

/** The machine-readable `code` from the error envelope, if any. */
export function errorCode(error: unknown): string | undefined {
  return errorBody(error)?.code;
}

export function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message || fallback;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

/* -------------------------------------------------------------------------- */
/* Endpoints                                                                  */
/* -------------------------------------------------------------------------- */

export const api = {
  health: () => apiFetch<HealthResponse>("/health/"),

  /** Endpoints that never involve a token, so they can be called directly. */
  auth: {
    register: (payload: RegisterPayload) =>
      apiFetch<RegisterResponse>("/auth/register/", {
        method: "POST",
        json: payload,
      }),

    resendOtp: (email: string) =>
      apiFetch<MessageResponse>("/auth/resend-otp/", {
        method: "POST",
        json: { email },
      }),

    requestPasswordReset: (email: string) =>
      apiFetch<MessageResponse>("/auth/password-reset/", {
        method: "POST",
        json: { email },
      }),

    confirmPasswordReset: (payload: {
      email: string;
      code: string;
      new_password: string;
      confirm_password: string;
    }) =>
      apiFetch<MessageResponse>("/auth/password-reset/confirm/", {
        method: "POST",
        json: payload,
      }),
  },

  /** Endpoints that need a signed-in user's access token. */
  me: {
    get: (token: string) => apiFetch<AuthUser>("/auth/me/", { token }),

    update: (token: string, payload: { full_name?: string; phone?: string }) =>
      apiFetch<AuthUser>("/auth/me/", {
        method: "PATCH",
        token,
        json: payload,
      }),

    changePassword: (
      token: string,
      payload: {
        current_password: string;
        new_password: string;
        confirm_password: string;
      },
    ) =>
      apiFetch<MessageResponse>("/auth/change-password/", {
        method: "POST",
        token,
        json: payload,
      }),
  },
};
