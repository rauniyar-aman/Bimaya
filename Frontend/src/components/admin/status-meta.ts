import type { StatusVariant } from "@/components/ui/status-pill";
import type {
  KycStatus,
  PolicyStatus,
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
