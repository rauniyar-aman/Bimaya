import type { PurchaseStatus } from "@/lib/api";
import type { StatusVariant } from "@/components/ui/status-pill";

interface StatusMeta {
  variant: StatusVariant;
  label: string;
  /** Short line explaining what the status means for the customer. */
  hint: string;
}

/** Maps a purchase's lifecycle status to its pill styling and plain-language copy. */
export const PURCHASE_STATUS_META: Record<PurchaseStatus, StatusMeta> = {
  ACTIVE: {
    variant: "active",
    label: "Active",
    hint: "Your cover is live. Keep your policy number handy for any claim.",
  },
  PENDING_PAYMENT: {
    variant: "pending",
    label: "Payment pending",
    hint: "Finish paying to move this policy forward.",
  },
  PAID: {
    variant: "info",
    label: "Paid — under review",
    hint: "We have your payment. Our team is verifying your KYC and payment.",
  },
  FORWARDED: {
    variant: "info",
    label: "With provider",
    hint: "Sent to the insurer to issue your policy. You'll get a policy number shortly.",
  },
  EXPIRED: {
    variant: "expired",
    label: "Expired",
    hint: "This policy has reached the end of its term.",
  },
  CANCELLED: {
    variant: "failed",
    label: "Cancelled",
    hint: "This purchase was cancelled before payment.",
  },
};
