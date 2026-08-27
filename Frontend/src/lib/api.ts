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
/* Marketplace shapes                                                         */
/* -------------------------------------------------------------------------- */

export type PremiumFrequency = "MONTHLY" | "QUARTERLY" | "YEARLY" | "ONE_TIME";
export type PolicyStatus = "DRAFT" | "PENDING" | "APPROVED" | "INACTIVE";
export type KycStatus = "PENDING" | "VERIFIED" | "REJECTED";

/** DRF page — `/policies/` and `/provider/policies/` are paginated. */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CategoryLight {
  id: number;
  name: string;
  slug: string;
  icon: string;
}

export interface InsuranceCategory extends CategoryLight {
  description: string;
  order: number;
  policy_count: number;
}

export interface ProviderLight {
  id: number;
  company_name: string;
  slug: string;
  logo: string | null;
}

export interface ProviderPublic extends ProviderLight {
  description: string;
  website: string;
}

/** Compact policy shape for cards, search results and category pages. */
export interface PolicySummary {
  id: number;
  name: string;
  slug: string;
  summary: string;
  premium: string;
  premium_frequency: PremiumFrequency;
  coverage_amount: string;
  term_months: number;
  is_featured: boolean;
  category: CategoryLight;
  provider: ProviderLight;
}

/** Full public policy for the detail page. */
export interface Policy extends PolicySummary {
  description: string;
  min_age: number | null;
  max_age: number | null;
  features: string[];
  add_ons: string[];
  terms: string;
  provider: ProviderPublic;
  created_at: string;
}

/** Normalised fields for the side-by-side comparison table. */
export interface PolicyCompare {
  id: number;
  name: string;
  slug: string;
  summary: string;
  premium: string;
  premium_frequency: PremiumFrequency;
  coverage_amount: string;
  term_months: number;
  min_age: number | null;
  max_age: number | null;
  features: string[];
  add_ons: string[];
  category: CategoryLight;
  provider: ProviderLight;
}

export interface PolicyListParams {
  category?: string;
  search?: string;
  ordering?: string;
  premium_min?: string | number;
  premium_max?: string | number;
  coverage_min?: string | number;
  premium_frequency?: PremiumFrequency;
  featured?: boolean;
  page?: string | number;
}

/* Provider-facing shapes (own profile + own policies). */

export interface ProviderProfile {
  id: number;
  company_name: string;
  slug: string;
  registration_number: string;
  description: string;
  logo: string | null;
  website: string;
  support_email: string;
  support_phone: string;
  kyc_status: KycStatus;
  is_approved: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderProfileInput {
  company_name: string;
  registration_number?: string;
  description?: string;
  website?: string;
  support_email?: string;
  support_phone?: string;
}

/** A provider's own policy — `category` is the write PK, `category_detail` the read shape. */
export interface ProviderPolicy {
  id: number;
  name: string;
  slug: string;
  summary: string;
  description: string;
  category: number;
  category_detail: CategoryLight;
  premium: string;
  premium_frequency: PremiumFrequency;
  coverage_amount: string;
  term_months: number;
  min_age: number | null;
  max_age: number | null;
  features: string[];
  add_ons: string[];
  terms: string;
  status: PolicyStatus;
  is_featured: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderPolicyInput {
  name: string;
  summary?: string;
  description?: string;
  category: number;
  premium: string;
  premium_frequency: PremiumFrequency;
  coverage_amount: string;
  term_months: number;
  min_age?: number | null;
  max_age?: number | null;
  features?: string[];
  add_ons?: string[];
  terms?: string;
}

/* Customer-facing shapes (purchases + payments). */

export type PurchaseStatus = "PENDING_PAYMENT" | "ACTIVE" | "EXPIRED" | "CANCELLED";
export type PaymentGateway = "ESEWA" | "KHALTI";

/** A customer's purchase of a policy, with the policy nested for one-request rendering. */
export interface PolicyPurchase {
  id: number;
  policy: PolicySummary;
  nominee_name: string;
  nominee_relationship: string;
  nominee_contact: string;
  status: PurchaseStatus;
  policy_number: string | null;
  start_date: string | null;
  end_date: string | null;
  renewal_reminder_sent: boolean;
  created_at: string;
  updated_at: string;
}

export interface PolicyPurchaseInput {
  policy: number;
  nominee_name: string;
  nominee_relationship: string;
  nominee_contact: string;
}

export interface PaymentInitiateInput {
  policy_purchase_id: number;
  gateway: PaymentGateway;
}

/** What a gateway needs to take over: eSewa returns a form to auto-submit, Khalti a URL to follow. */
export interface PaymentInitiateResult {
  payment_id: number;
  gateway: PaymentGateway;
  payment_url: string;
  fields?: Record<string, string>;
  pidx?: string;
}

export interface PaymentCallbackResult {
  detail: string;
  status: string;
}

/**
 * Signature of the `authFetch` provided by `useAuth()`. Provider endpoints take
 * it as their first argument so calls stay typed without re-threading the token.
 */
export type AuthFetch = <T>(path: string, options?: ApiFetchOptions) => Promise<T>;

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

/** Serialise a params object to a query string, dropping empty values. */
function toQuery(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

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

  /** Public catalog — no token, safe to call from the server or the browser. */
  categories: {
    list: () =>
      apiFetch<InsuranceCategory[]>("/categories/", { cache: "no-store" }),

    get: (slug: string) =>
      apiFetch<InsuranceCategory>(`/categories/${slug}/`, { cache: "no-store" }),
  },

  policies: {
    list: (params: PolicyListParams = {}) =>
      apiFetch<Paginated<PolicySummary>>(
        `/policies/${toQuery(params as Record<string, unknown>)}`,
        {
          cache: "no-store",
        },
      ),

    get: (slug: string) =>
      apiFetch<Policy>(`/policies/${slug}/`, { cache: "no-store" }),

    compare: (ids: number[]) =>
      apiFetch<PolicyCompare[]>(`/policies/compare/?ids=${ids.join(",")}`, {
        cache: "no-store",
      }),
  },

  /**
   * Provider-only endpoints. Each takes the `authFetch` from `useAuth()` so the
   * access token is injected and refreshed on 401 automatically.
   */
  provider: {
    getProfile: (authFetch: AuthFetch) =>
      authFetch<ProviderProfile>("/provider/profile/"),

    saveProfile: (
      authFetch: AuthFetch,
      payload: ProviderProfileInput,
      method: "PUT" | "PATCH" = "PUT",
    ) => authFetch<ProviderProfile>("/provider/profile/", { method, json: payload }),

    listPolicies: (authFetch: AuthFetch) =>
      authFetch<Paginated<ProviderPolicy>>("/provider/policies/"),

    getPolicy: (authFetch: AuthFetch, id: number) =>
      authFetch<ProviderPolicy>(`/provider/policies/${id}/`),

    createPolicy: (authFetch: AuthFetch, payload: ProviderPolicyInput) =>
      authFetch<ProviderPolicy>("/provider/policies/", {
        method: "POST",
        json: payload,
      }),

    updatePolicy: (
      authFetch: AuthFetch,
      id: number,
      payload: Partial<ProviderPolicyInput>,
    ) =>
      authFetch<ProviderPolicy>(`/provider/policies/${id}/`, {
        method: "PATCH",
        json: payload,
      }),

    deletePolicy: (authFetch: AuthFetch, id: number) =>
      authFetch<void>(`/provider/policies/${id}/`, { method: "DELETE" }),

    submitPolicy: (authFetch: AuthFetch, id: number) =>
      authFetch<ProviderPolicy>(`/provider/policies/${id}/submit/`, {
        method: "POST",
      }),
  },

  /** Customer-only endpoints for buying a policy and paying for it. */
  purchases: {
    list: (authFetch: AuthFetch) =>
      authFetch<Paginated<PolicyPurchase>>("/purchases/"),

    get: (authFetch: AuthFetch, id: number) =>
      authFetch<PolicyPurchase>(`/purchases/${id}/`),

    create: (authFetch: AuthFetch, payload: PolicyPurchaseInput) =>
      authFetch<PolicyPurchase>("/purchases/", { method: "POST", json: payload }),

    cancel: (authFetch: AuthFetch, id: number) =>
      authFetch<PolicyPurchase>(`/purchases/${id}/cancel/`, { method: "POST" }),
  },

  payments: {
    initiate: (authFetch: AuthFetch, payload: PaymentInitiateInput) =>
      authFetch<PaymentInitiateResult>("/payments/initiate/", {
        method: "POST",
        json: payload,
      }),

    /** Public — the browser forwards whatever the gateway put in the redirect. */
    confirm: (gateway: PaymentGateway, params: URLSearchParams) =>
      apiFetch<PaymentCallbackResult>(
        `/payments/${gateway.toLowerCase()}/callback/?${params.toString()}`,
        { noCredentials: true },
      ),
  },
};
