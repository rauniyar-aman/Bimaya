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
  /**
   * Body to send as multipart form data (for file uploads). The browser sets
   * the `Content-Type` (with the boundary), so we never set it ourselves.
   */
  form?: FormData;
  /**
   * Read the response as a binary `Blob` instead of JSON/text — for file
   * downloads (e.g. generated PDFs). A JSON error envelope is still parsed on
   * failure so `errorMessage`/`errorCode` keep working.
   */
  blob?: boolean;
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
    form,
    blob,
    baseUrl = API_BASE_URL,
    ...rest
  } = options;
  const url = path.startsWith("http") ? path : `${baseUrl}${path}`;
  // JSON is serialised and content-typed; FormData is sent as-is so the browser
  // can set the multipart boundary; a raw body is passed straight through.
  const payload = json !== undefined ? JSON.stringify(json) : form ?? body;
  const isMultipart = form !== undefined;

  const res = await fetch(url, {
    credentials: noCredentials ? "omit" : "include",
    headers: {
      Accept: "application/json",
      ...(payload !== undefined && !isMultipart
        ? { "Content-Type": "application/json" }
        : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(payload !== undefined ? { body: payload } : {}),
    ...rest,
  });

  // Binary downloads: read the body as a Blob, but still surface a JSON error
  // envelope on failure (the backend returns one even for a PDF endpoint).
  if (blob) {
    if (!res.ok) {
      const errData = await res.json().catch(() => null);
      const detail =
        errData && typeof errData === "object" && "detail" in errData
          ? String((errData as { detail: unknown }).detail)
          : res.statusText;
      throw new ApiError(detail || "Request failed", res.status, errData);
    }
    return (await res.blob()) as T;
  }

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
  password: string;
  confirm_password: string;
}

/** Public enquiry from the "For insurance providers" onboarding form. */
export interface ProviderLeadInput {
  company_name: string;
  contact_name: string;
  email: string;
  phone?: string;
  message?: string;
}

/** Public enquiry from the "Contact" page — no company. */
export interface ContactLeadInput {
  contact_name: string;
  email: string;
  phone?: string;
  message?: string;
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

/* AI advisor shapes (rule-based recommendations + flag-gated chat). */

/** Optional criteria for the recommendation engine — all fields are optional. */
export interface RecommendationInput {
  category?: string;
  budget_max?: string | number;
  coverage_min?: string | number;
  age?: string | number;
  term_max?: string | number;
  limit?: number;
}

/** A policy summary annotated with its rule-based match score and reasons. */
export interface RecommendedPolicy extends PolicySummary {
  match_score: number;
  reasons: string[];
}

/** One turn of the client-side chat history sent back for context. */
export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

/** The assistant's reply to a chat message. */
export interface ChatReply {
  reply: string;
}

/* Provider-facing shapes (own profile + own policies). */

/** A member's role within a provider organisation. */
export type ProviderRole = "OWNER" | "STAFF" | "VIEWER";

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
  /** Platform commission percent on each sale — set by admins, read-only here. */
  commission_rate: string;
  /** The signed-in user's role here — drives which write actions the UI shows. */
  my_role: ProviderRole | null;
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

export type PurchaseStatus =
  | "PENDING_PAYMENT"
  | "PAID"
  | "FORWARDED"
  | "ACTIVE"
  | "EXPIRED"
  | "CANCELLED";
export type PaymentGateway = "ESEWA" | "KHALTI";

export type MaritalStatus = "SINGLE" | "MARRIED" | "OTHER";
export type DocumentType = "PASSPORT" | "CITIZENSHIP" | "NID";

/** A customer's KYC record (own reusable, or a beneficiary's). */
export interface CustomerKyc {
  id: number;
  is_self: boolean;
  full_name: string;
  email: string;
  phone: string;
  date_of_birth: string | null;
  marital_status: MaritalStatus | "";
  family_details: string;
  temporary_address: string;
  permanent_address: string;
  document_type: DocumentType;
  document_number: string;
  document_front: string | null;
  document_back: string | null;
  status: KycStatus;
  review_note: string;
  created_at: string;
  updated_at: string;
}

/** Fields the customer fills in; images are appended to FormData separately. */
export interface CustomerKycInput {
  full_name: string;
  email?: string;
  phone?: string;
  date_of_birth?: string;
  marital_status?: MaritalStatus | "";
  family_details?: string;
  temporary_address?: string;
  permanent_address: string;
  document_type: DocumentType;
  document_number: string;
}

/** Compact KYC summary nested on a purchase. */
export interface KycSummary {
  id: number;
  is_self: boolean;
  full_name: string;
  document_type: DocumentType;
  status: KycStatus;
}

/** A customer's purchase of a policy, with the policy nested for one-request rendering. */
export interface PolicyPurchase {
  id: number;
  policy: PolicySummary;
  kyc: KycSummary | null;
  insured_is_self: boolean;
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
  kyc: number;
  insured_is_self: boolean;
  nominee_name: string;
  nominee_relationship: string;
  nominee_contact: string;
}

/** A purchase awaiting issuance in the provider's queue. */
export interface ProviderIssuanceItem {
  id: number;
  policy: PolicySummary;
  kyc: KycSummary | null;
  insured_is_self: boolean;
  nominee_name: string;
  nominee_relationship: string;
  nominee_contact: string;
  status: PurchaseStatus;
  created_at: string;
}

/** A purchase on one of the provider's policies, with the buying customer's name. */
export interface ProviderPurchase extends PolicyPurchase {
  customer_name: string;
}

export interface ProviderPurchaseListParams {
  status?: PurchaseStatus;
  search?: string;
  page?: number;
}

/** A provider's own payout row: the commission split on one issued sale. */
export interface ProviderPayout {
  id: number;
  policy_name: string;
  policy_number: string | null;
  gross_amount: string;
  commission_rate: string;
  commission_amount: string;
  net_amount: string;
  status: PayoutStatus;
  paid_at: string | null;
  created_at: string;
}

export interface ProviderPayoutListParams {
  status?: PayoutStatus;
  search?: string;
  page?: number;
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

/* -------------------------------------------------------------------------- */
/* Claims shapes                                                              */
/* -------------------------------------------------------------------------- */

export type ClaimStatus =
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "MORE_INFO"
  | "APPROVED"
  | "REJECTED"
  | "SETTLED";

export type ClaimPayoutStatus = "INITIATED" | "SUCCESS" | "FAILED";

/**
 * A supporting file on a claim. The file itself is fetched through the
 * authenticated download endpoint (never a raw media URL) — these are sensitive
 * medical/police/financial documents — so only its metadata is exposed here.
 */
export interface ClaimDocument {
  id: number;
  caption: string;
  created_at: string;
}

/** A simulated payout attached to an approved claim (no real money moves). */
export interface ClaimPayoutSummary {
  id: number;
  gateway: PaymentGateway;
  amount: string;
  status: ClaimPayoutStatus;
  gateway_reference: string | null;
  paid_at: string | null;
  created_at: string;
}

/** The policy purchase a claim is filed against, with the policy nested. */
export interface ClaimPurchaseSummary {
  id: number;
  policy: PolicySummary;
  policy_number: string | null;
  status: PurchaseStatus;
}

/** One message in a claim's customer↔insurer thread. */
export interface ClaimMessage {
  id: number;
  /** Whose side posted it, denormalised so the UI can label You/Insurer. */
  author_role: UserRole;
  body: string;
  created_at: string;
}

/** A customer's insurance claim, with purchase, documents, payouts and thread nested. */
export interface Claim {
  id: number;
  purchase: ClaimPurchaseSummary;
  status: ClaimStatus;
  incident_date: string;
  incident_location: string;
  description: string;
  claimed_amount: string;
  approved_amount: string | null;
  review_note: string;
  documents: ClaimDocument[];
  payouts: ClaimPayoutSummary[];
  messages: ClaimMessage[];
  decided_at: string | null;
  settled_at: string | null;
  created_at: string;
  updated_at: string;
}

/** The simulated gateway session returned when a payout is initiated. */
export interface ClaimPayoutInitiateResult {
  payout_id: number;
  gateway: PaymentGateway;
  amount: string;
  reference: string;
  status: ClaimPayoutStatus;
  simulated: boolean;
}

/* -------------------------------------------------------------------------- */
/* Notification shapes                                                        */
/* -------------------------------------------------------------------------- */

export type NotificationType =
  | "WELCOME"
  | "PURCHASE_CREATED"
  | "PAYMENT_CONFIRMED"
  | "PAYMENT_FAILED"
  | "PURCHASE_FORWARDED"
  | "POLICY_ISSUED"
  | "RENEWAL_REMINDER"
  | "CLAIM_SUBMITTED"
  | "CLAIM_UNDER_REVIEW"
  | "CLAIM_MORE_INFO"
  | "CLAIM_APPROVED"
  | "CLAIM_REJECTED"
  | "CLAIM_SETTLED"
  | "KYC_VERIFIED"
  | "KYC_REJECTED"
  | "PROVIDER_APPROVED"
  | "PROVIDER_NEW_ISSUANCE"
  | "PROVIDER_NEW_CLAIM";

/** An in-app notification for the signed-in user. */
export interface AppNotification {
  id: number;
  type: NotificationType;
  title: string;
  body: string;
  url: string;
  read_at: string | null;
  is_read: boolean;
  created_at: string;
}

/**
 * Whether browser push is switched on server-side, and the VAPID public key to
 * subscribe with. `enabled` is false (and the key blank) until an admin turns
 * push on and configures a keypair — the toggle uses this to show a graceful
 * "not available yet" state rather than failing.
 */
export interface PushKeyInfo {
  enabled: boolean;
  public_key: string;
}

/* -------------------------------------------------------------------------- */
/* Admin-panel shapes                                                         */
/* -------------------------------------------------------------------------- */

/** A provider row in the admin approvals table, with the owning account. */
export interface AdminProvider {
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
  commission_rate: string;
  owner_email: string;
  owner_name: string;
  policy_count: number;
  created_at: string;
  updated_at: string;
}

/**
 * A full KYC record for admin review. Document images are fetched through the
 * authenticated download endpoints — never raw media URLs — so only the
 * availability flags (`has_front`/`has_back`) are exposed here.
 */
export interface AdminKyc {
  id: number;
  customer_email: string;
  is_self: boolean;
  full_name: string;
  email: string;
  phone: string;
  date_of_birth: string | null;
  marital_status: MaritalStatus | "";
  family_details: string;
  temporary_address: string;
  permanent_address: string;
  document_type: DocumentType;
  document_number: string;
  has_front: boolean;
  has_back: boolean;
  status: KycStatus;
  review_note: string;
  created_at: string;
  updated_at: string;
}

/** A user row in the admin users table. */
export interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  date_joined: string;
}

/** A single user with activity counts. */
export interface AdminUserDetail extends AdminUser {
  purchase_count: number;
  claim_count: number;
}

/** A policy row in the admin all-policies table (reuses the public list shape plus status). */
export interface AdminPolicy extends PolicySummary {
  status: PolicyStatus;
  created_at: string;
}

/** A purchase row in the admin verification table — the purchase shape plus the buying customer. */
export interface AdminPurchase extends PolicyPurchase {
  customer_email: string;
  customer_name: string;
}

/** What a provider is owed for an issued policy, net of platform commission. */
export type PayoutStatus = "PENDING" | "PAID";

export interface AdminPayout {
  id: number;
  provider_name: string;
  policy_name: string;
  policy_number: string | null;
  gross_amount: string;
  commission_rate: string;
  commission_amount: string;
  net_amount: string;
  status: PayoutStatus;
  paid_at: string | null;
  created_at: string;
}

export interface AdminPayoutListParams {
  status?: PayoutStatus;
  provider?: number;
  search?: string;
  page?: number;
}

export interface AdminProviderListParams {
  is_approved?: boolean;
  kyc_status?: KycStatus;
  search?: string;
  page?: number;
}

/** One person in a provider organisation: the owner or an added staff/viewer. */
export interface ProviderMember {
  user_id: number;
  /** Null for the owner (who is `Provider.user`, not a membership row). */
  membership_id: number | null;
  email: string;
  full_name: string;
  role: ProviderRole;
  is_active: boolean;
  date_joined: string;
}

/** Admin input to add a staff/viewer to a provider organisation. */
export interface ProviderMemberInput {
  email: string;
  full_name?: string;
  password: string;
  role: "STAFF" | "VIEWER";
}

export interface AdminKycListParams {
  status?: KycStatus;
  is_self?: boolean;
  search?: string;
  page?: number;
}

export interface AdminPurchaseListParams {
  status?: PurchaseStatus;
  search?: string;
  page?: number;
}

export interface AdminUserListParams {
  role?: UserRole;
  is_verified?: boolean;
  is_active?: boolean;
  search?: string;
  page?: number;
}

export interface AdminPolicyListParams {
  status?: PolicyStatus;
  provider?: number;
  category?: number;
  is_featured?: boolean;
  search?: string;
  page?: number;
}

/* -------------------------------------------------------------------------- */
/* Analytics shapes                                                           */
/* -------------------------------------------------------------------------- */

/**
 * A headline metric for a stat card. `value` is a plain number for counts and a
 * decimal string for currency amounts; `format` says which, so the frontend
 * renders it as a raw count or through `formatNpr`.
 */
export interface AnalyticsStat {
  key: string;
  label: string;
  value: number | string;
  format: "count" | "currency";
}

/** One labelled bar in a breakdown chart (status counts, users by role, …). */
export interface AnalyticsBreakdown {
  key: string;
  label: string;
  value: number;
}

/** One month in the trend series: a purchase count and premium collected. */
export interface AnalyticsMonth {
  /** `YYYY-MM`. */
  month: string;
  /** Short month label, e.g. `Sep`. */
  label: string;
  purchases: number;
  /** Decimal string (premium collected that month). */
  premium: string;
}

/** Fields shared by the admin and provider analytics payloads. */
export interface AnalyticsData {
  stats: AnalyticsStat[];
  purchases_by_status: AnalyticsBreakdown[];
  claims_by_status: AnalyticsBreakdown[];
  monthly: AnalyticsMonth[];
}

/** Platform-wide analytics for the admin dashboard. */
export interface AdminAnalytics extends AnalyticsData {
  users_by_role: AnalyticsBreakdown[];
  providers: { total: number; approved: number; pending: number };
  queues: {
    pending_providers: number;
    pending_kyc: number;
    paid_purchases: number;
  };
}

/** Analytics scoped to a single provider's own policies. */
export type ProviderAnalytics = AnalyticsData;

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

  /** Public enquiries — no token. Provider onboarding and contact messages. */
  leads: {
    create: (payload: ProviderLeadInput) =>
      apiFetch<MessageResponse>("/provider-leads/", {
        method: "POST",
        json: payload,
      }),
    contact: (payload: ContactLeadInput) =>
      apiFetch<MessageResponse>("/contact-enquiries/", {
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

  /** AI advisor — public recommendations + authenticated flag-gated chat. */
  assistant: {
    /** Rule-based ranking of the public catalog — no token, no LLM. */
    recommend: (payload: RecommendationInput = {}) =>
      apiFetch<RecommendedPolicy[]>("/assistant/recommend/", {
        method: "POST",
        json: payload,
      }),

    /** Free-form insurance Q&A. Only answers when the flag + key are set. */
    chat: (
      authFetch: AuthFetch,
      payload: { message: string; history?: ChatTurn[] },
    ) =>
      authFetch<ChatReply>("/assistant/chat/", {
        method: "POST",
        json: payload,
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

    /** Analytics scoped to this provider's own policies. */
    analytics: (authFetch: AuthFetch) =>
      authFetch<ProviderAnalytics>("/provider/analytics/"),

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

    /** Take a live (APPROVED) policy off the marketplace; relist via submitPolicy. */
    deactivatePolicy: (authFetch: AuthFetch, id: number) =>
      authFetch<ProviderPolicy>(`/provider/policies/${id}/deactivate/`, {
        method: "POST",
      }),

    /** Every purchase on this provider's policies (sales history), newest first. */
    listPurchases: (authFetch: AuthFetch, params: ProviderPurchaseListParams = {}) =>
      authFetch<Paginated<ProviderPurchase>>(
        `/provider/purchases/${toQuery(params as Record<string, unknown>)}`,
      ),

    /** This provider's commission payouts (read-only ledger), newest first. */
    listPayouts: (authFetch: AuthFetch, params: ProviderPayoutListParams = {}) =>
      authFetch<Paginated<ProviderPayout>>(
        `/provider/payouts/${toQuery(params as Record<string, unknown>)}`,
      ),

    /** Purchases forwarded to this provider, waiting for a policy number. */
    listIssuance: (authFetch: AuthFetch) =>
      authFetch<Paginated<ProviderIssuanceItem>>("/provider/issuance/"),

    /** Issue a forwarded purchase by entering the provider's own policy number. */
    issue: (authFetch: AuthFetch, id: number, policy_number: string) =>
      authFetch<PolicyPurchase>(`/provider/issuance/${id}/issue/`, {
        method: "POST",
        json: { policy_number },
      }),

    /** Claims filed on this provider's policies, newest first; optional `?status=`. */
    listClaims: (authFetch: AuthFetch, status?: ClaimStatus) =>
      authFetch<Paginated<Claim>>(`/provider/claims/${toQuery({ status })}`),

    getClaim: (authFetch: AuthFetch, id: number) =>
      authFetch<Claim>(`/provider/claims/${id}/`),

    /** Move a submitted claim into review (required before any decision). */
    startReviewClaim: (authFetch: AuthFetch, id: number) =>
      authFetch<Claim>(`/provider/claims/${id}/start-review/`, { method: "POST" }),

    /** Bounce a claim back to the customer for more information. */
    requestInfoClaim: (authFetch: AuthFetch, id: number, note: string) =>
      authFetch<Claim>(`/provider/claims/${id}/request-info/`, {
        method: "POST",
        json: { note },
      }),

    /** Approve a claim for a payout amount. */
    approveClaim: (
      authFetch: AuthFetch,
      id: number,
      payload: { approved_amount: string; note?: string },
    ) =>
      authFetch<Claim>(`/provider/claims/${id}/approve/`, {
        method: "POST",
        json: payload,
      }),

    /** Reject a claim with a reason. */
    rejectClaim: (authFetch: AuthFetch, id: number, note: string) =>
      authFetch<Claim>(`/provider/claims/${id}/reject/`, {
        method: "POST",
        json: { note },
      }),

    /** Start a simulated payout for an approved claim (no real money moves). */
    payoutInitiateClaim: (authFetch: AuthFetch, id: number, gateway: PaymentGateway) =>
      authFetch<ClaimPayoutInitiateResult>(
        `/provider/claims/${id}/payout/initiate/`,
        { method: "POST", json: { gateway } },
      ),

    /** Confirm the simulated payout, settling the claim. */
    payoutConfirmClaim: (authFetch: AuthFetch, id: number, payoutId?: number) =>
      authFetch<Claim>(`/provider/claims/${id}/payout/confirm/`, {
        method: "POST",
        json: payoutId ? { payout_id: payoutId } : {},
      }),

    /** Post a message to a claim's thread (provider side); the customer is notified. */
    postClaimMessage: (authFetch: AuthFetch, id: number, body: string) =>
      authFetch<Claim>(`/provider/claims/${id}/messages/`, {
        method: "POST",
        json: { body },
      }),
  },

  /** Customer KYC — the reusable self record and per-beneficiary records. */
  kyc: {
    /** The customer's own reusable KYC, or `null` when not set up yet. */
    getSelf: async (authFetch: AuthFetch): Promise<CustomerKyc | null> => {
      try {
        return await authFetch<CustomerKyc>("/kyc/self/");
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },

    /** Create or update the reusable self KYC (multipart, with document images). */
    saveSelf: (authFetch: AuthFetch, form: FormData, method: "PUT" | "PATCH" = "PUT") =>
      authFetch<CustomerKyc>("/kyc/self/", { method, form }),

    /** Capture a fresh beneficiary KYC when buying for someone else. */
    createBeneficiary: (authFetch: AuthFetch, form: FormData) =>
      authFetch<CustomerKyc>("/kyc/beneficiary/", { method: "POST", form }),
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

    /** Download the Certificate of Insurance PDF (available once issued). */
    certificate: (authFetch: AuthFetch, id: number) =>
      authFetch<Blob>(`/purchases/${id}/certificate/`, { blob: true }),

    /** Download the payment receipt PDF (available once a payment succeeds). */
    receipt: (authFetch: AuthFetch, id: number) =>
      authFetch<Blob>(`/purchases/${id}/receipt/`, { blob: true }),
  },

  /** Customer-only endpoints for filing and tracking insurance claims. */
  claims: {
    list: (authFetch: AuthFetch) => authFetch<Paginated<Claim>>("/claims/"),

    get: (authFetch: AuthFetch, id: number) => authFetch<Claim>(`/claims/${id}/`),

    /** File a claim (multipart — one or more supporting documents attached). */
    create: (authFetch: AuthFetch, form: FormData) =>
      authFetch<Claim>("/claims/", { method: "POST", form }),

    /** Resubmit a claim sent back for more information (multipart, +documents). */
    resubmit: (authFetch: AuthFetch, id: number, form: FormData) =>
      authFetch<Claim>(`/claims/${id}/resubmit/`, { method: "POST", form }),

    /** Download a supporting document via the authenticated owner/underwriter route. */
    document: (authFetch: AuthFetch, claimId: number, docId: number) =>
      authFetch<Blob>(`/claims/${claimId}/documents/${docId}/`, { blob: true }),

    /** Post a message to a claim's thread (customer side); the insurer is notified. */
    postMessage: (authFetch: AuthFetch, id: number, body: string) =>
      authFetch<Claim>(`/claims/${id}/messages/`, {
        method: "POST",
        json: { body },
      }),
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

  /** In-app notifications for the signed-in user. */
  notifications: {
    list: (authFetch: AuthFetch, params: { unread?: boolean; page?: number } = {}) =>
      authFetch<Paginated<AppNotification>>(
        `/notifications/${toQuery({
          unread: params.unread ? "true" : undefined,
          page: params.page,
        })}`,
      ),

    unreadCount: (authFetch: AuthFetch) =>
      authFetch<{ count: number }>("/notifications/unread-count/"),

    markRead: (authFetch: AuthFetch, id: number) =>
      authFetch<AppNotification>(`/notifications/${id}/read/`, { method: "POST" }),

    markAllRead: (authFetch: AuthFetch) =>
      authFetch<{ updated: number }>("/notifications/read-all/", { method: "POST" }),

    /** Whether browser push is on, plus the VAPID public key to subscribe with. */
    pushVapidKey: (authFetch: AuthFetch) =>
      authFetch<PushKeyInfo>("/notifications/push/vapid-key/"),

    /**
     * Register this browser's push subscription. Send the browser's own
     * `PushSubscription.toJSON()` — the backend reads `endpoint` and `keys`.
     */
    subscribePush: (authFetch: AuthFetch, subscription: PushSubscriptionJSON) =>
      authFetch<{ subscribed: boolean }>("/notifications/push/subscribe/", {
        method: "POST",
        json: subscription,
      }),

    unsubscribePush: (authFetch: AuthFetch, endpoint: string) =>
      authFetch<{ unsubscribed: boolean }>("/notifications/push/unsubscribe/", {
        method: "POST",
        json: { endpoint },
      }),
  },

  /**
   * Admin-panel endpoints (`/admin/...`), all gated by `IsPlatformAdmin`. These
   * back the branded in-app `/admin` area; the Django admin remains the
   * low-level fallback.
   */
  admin: {
    /* Providers */
    listProviders: (authFetch: AuthFetch, params: AdminProviderListParams = {}) =>
      authFetch<Paginated<AdminProvider>>(
        `/admin/providers/${toQuery(params as Record<string, unknown>)}`,
      ),

    getProvider: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminProvider>(`/admin/providers/${id}/`),

    approveProvider: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminProvider>(`/admin/providers/${id}/approve/`, {
        method: "POST",
      }),

    revokeProvider: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminProvider>(`/admin/providers/${id}/revoke/`, {
        method: "POST",
      }),

    /** Set the platform commission percent charged on a provider's sales (0–100). */
    setProviderCommission: (authFetch: AuthFetch, id: number, rate: string) =>
      authFetch<AdminProvider>(`/admin/providers/${id}/commission/`, {
        method: "POST",
        json: { commission_rate: rate },
      }),

    /* Provider team members — the owner (read-only here) plus added staff/viewers */
    listProviderMembers: (authFetch: AuthFetch, providerId: number) =>
      authFetch<ProviderMember[]>(`/admin/providers/${providerId}/members/`),

    addProviderMember: (
      authFetch: AuthFetch,
      providerId: number,
      payload: ProviderMemberInput,
    ) =>
      authFetch<ProviderMember>(`/admin/providers/${providerId}/members/`, {
        method: "POST",
        json: payload,
      }),

    updateProviderMemberRole: (
      authFetch: AuthFetch,
      providerId: number,
      membershipId: number,
      role: "STAFF" | "VIEWER",
    ) =>
      authFetch<ProviderMember>(
        `/admin/providers/${providerId}/members/${membershipId}/`,
        { method: "PATCH", json: { role } },
      ),

    removeProviderMember: (
      authFetch: AuthFetch,
      providerId: number,
      membershipId: number,
    ) =>
      authFetch<void>(`/admin/providers/${providerId}/members/${membershipId}/`, {
        method: "DELETE",
      }),

    /* KYC */
    listKyc: (authFetch: AuthFetch, params: AdminKycListParams = {}) =>
      authFetch<Paginated<AdminKyc>>(
        `/admin/kyc/${toQuery(params as Record<string, unknown>)}`,
      ),

    getKyc: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminKyc>(`/admin/kyc/${id}/`),

    /** Download a KYC document image (PII) via the authenticated admin route. */
    kycDocument: (authFetch: AuthFetch, id: number, side: "front" | "back") =>
      authFetch<Blob>(`/admin/kyc/${id}/document/${side}/`, { blob: true }),

    verifyKyc: (authFetch: AuthFetch, id: number) =>
      authFetch<CustomerKyc>(`/admin/kyc/${id}/verify/`, { method: "POST" }),

    rejectKyc: (authFetch: AuthFetch, id: number, note: string) =>
      authFetch<CustomerKyc>(`/admin/kyc/${id}/reject/`, {
        method: "POST",
        json: { note },
      }),

    /* Purchases */
    listPurchases: (authFetch: AuthFetch, params: AdminPurchaseListParams = {}) =>
      authFetch<Paginated<AdminPurchase>>(
        `/admin/purchases/${toQuery(params as Record<string, unknown>)}`,
      ),

    /** Verify payment + KYC and forward a paid purchase to its provider. */
    verifyAndForwardPurchase: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminPurchase>(`/admin/purchases/${id}/verify-and-forward/`, {
        method: "POST",
      }),

    /* Provider payouts (commission ledger) */
    listPayouts: (authFetch: AuthFetch, params: AdminPayoutListParams = {}) =>
      authFetch<Paginated<AdminPayout>>(
        `/admin/payouts/${toQuery(params as Record<string, unknown>)}`,
      ),

    /* Users */
    listUsers: (authFetch: AuthFetch, params: AdminUserListParams = {}) =>
      authFetch<Paginated<AdminUser>>(
        `/admin/users/${toQuery(params as Record<string, unknown>)}`,
      ),

    getUser: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminUserDetail>(`/admin/users/${id}/`),

    /** Suspend a user (deactivate their account so they can no longer sign in). */
    suspendUser: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminUser>(`/admin/users/${id}/suspend/`, { method: "POST" }),

    /** Reactivate a previously suspended user. */
    reactivateUser: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminUser>(`/admin/users/${id}/reactivate/`, { method: "POST" }),

    /* Policies */
    listPolicies: (authFetch: AuthFetch, params: AdminPolicyListParams = {}) =>
      authFetch<Paginated<AdminPolicy>>(
        `/admin/policies/${toQuery(params as Record<string, unknown>)}`,
      ),

    /** Approve a pending (or relist an inactive) policy onto the marketplace. */
    approvePolicy: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminPolicy>(`/admin/policies/${id}/approve/`, { method: "POST" }),

    /** Send a pending policy back to the provider for changes. */
    rejectPolicy: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminPolicy>(`/admin/policies/${id}/reject/`, { method: "POST" }),

    /** Take a live policy off the marketplace. */
    deactivatePolicy: (authFetch: AuthFetch, id: number) =>
      authFetch<AdminPolicy>(`/admin/policies/${id}/deactivate/`, { method: "POST" }),

    /* Reports (CSV export) — same filters + search as each list, every row. */
    exportProviders: (authFetch: AuthFetch, params: AdminProviderListParams = {}) =>
      authFetch<Blob>(
        `/admin/reports/providers/${toQuery(params as Record<string, unknown>)}`,
        { blob: true },
      ),

    exportUsers: (authFetch: AuthFetch, params: AdminUserListParams = {}) =>
      authFetch<Blob>(
        `/admin/reports/users/${toQuery(params as Record<string, unknown>)}`,
        { blob: true },
      ),

    exportPolicies: (authFetch: AuthFetch, params: AdminPolicyListParams = {}) =>
      authFetch<Blob>(
        `/admin/reports/policies/${toQuery(params as Record<string, unknown>)}`,
        { blob: true },
      ),

    exportPurchases: (authFetch: AuthFetch, params: AdminPurchaseListParams = {}) =>
      authFetch<Blob>(
        `/admin/reports/purchases/${toQuery(params as Record<string, unknown>)}`,
        { blob: true },
      ),

    exportPayouts: (authFetch: AuthFetch, params: AdminPayoutListParams = {}) =>
      authFetch<Blob>(
        `/admin/reports/payouts/${toQuery(params as Record<string, unknown>)}`,
        { blob: true },
      ),

    /* Analytics */
    analytics: (authFetch: AuthFetch) =>
      authFetch<AdminAnalytics>("/admin/analytics/"),
  },
};
