import type { StatusVariant } from "@/components/ui/status-pill";
import type {
  KycStatus,
  PayoutStatus,
  PolicyStatus,
  ProviderRole,
  PurchaseStatus,
  UserRole,
} from "@/lib/api";

/** Status-pill variant + human label for each purchase status. */
export const PURCHASE_STATUS_META: Record<
  PurchaseStatus,
  { variant: StatusVariant; label: string }
> = {
  PENDING_PAYMENT: { variant: "pending", label: "Pending payment" },
  PAID: { variant: "info", label: "Paid — awaiting review" },
  FORWARDED: { variant: "info", label: "With provider" },
  ACTIVE: { variant: "active", label: "Active" },
  EXPIRED: { variant: "expired", label: "Expired" },
  CANCELLED: { variant: "failed", label: "Cancelled" },
};

export const KYC_STATUS_META: Record<
  KycStatus,
  { variant: StatusVariant; label: string }
> = {
  PENDING: { variant: "pending", label: "Pending" },
  VERIFIED: { variant: "active", label: "Verified" },
  REJECTED: { variant: "failed", label: "Rejected" },
};

export const POLICY_STATUS_META: Record<
  PolicyStatus,
  { variant: StatusVariant; label: string }
> = {
  DRAFT: { variant: "expired", label: "Draft" },
  PENDING: { variant: "pending", label: "Pending review" },
  APPROVED: { variant: "active", label: "Approved" },
  INACTIVE: { variant: "failed", label: "Inactive" },
};

export const ROLE_META: Record<UserRole, { variant: StatusVariant; label: string }> = {
  CUSTOMER: { variant: "info", label: "Customer" },
  PROVIDER: { variant: "pending", label: "Provider" },
  ADMIN: { variant: "active", label: "Admin" },
};

/** Status-pill variant + label for a provider payout's settlement state. */
export const PAYOUT_STATUS_META: Record<
  PayoutStatus,
  { variant: StatusVariant; label: string }
> = {
  PENDING: { variant: "pending", label: "Pending" },
  PAID: { variant: "active", label: "Paid" },
};

/**
 * The role one person holds inside a provider organisation. The owner is the
 * account the organisation was created under, so it reads as the active role;
 * every assignable role is informational.
 */
export const PROVIDER_ROLE_META: Record<
  ProviderRole,
  { variant: StatusVariant; label: string }
> = {
  OWNER: { variant: "active", label: "Owner" },
  COMPANY_ADMIN: { variant: "info", label: "Company Admin" },
  POLICY_MANAGER: { variant: "info", label: "Policy Manager" },
  CLAIMS_OFFICER: { variant: "info", label: "Claims Officer" },
  SALES_MANAGER: { variant: "info", label: "Sales Manager" },
  FINANCE_VIEWER: { variant: "info", label: "Finance Viewer" },
};
