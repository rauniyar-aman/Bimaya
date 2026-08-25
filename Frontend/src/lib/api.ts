/**
 * Typed client for the Bimaya REST API.
 *
 * The base URL points at the Django backend (`/api/v1`). Requests include
 * credentials so the httpOnly refresh-token cookie flows once auth lands.
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
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { noCredentials, headers, body, ...rest } = options;
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;

  const res = await fetch(url, {
    credentials: noCredentials ? "omit" : "include",
    headers: {
      Accept: "application/json",
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    ...(body !== undefined ? { body } : {}),
    ...rest,
  });

  const isJson = res.headers
    .get("content-type")
    ?.includes("application/json");
  const data = isJson
    ? await res.json().catch(() => null)
    : await res.text();

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : res.statusText;
    throw new ApiError(detail || "Request failed", res.status, data);
  }

  return data as T;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export const api = {
  health: () => apiFetch<HealthResponse>("/health/"),
};
