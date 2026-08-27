import type { PolicyStatus } from "@/lib/api";
import type { StatusVariant } from "@/components/ui/status-pill";

interface StatusMeta {
  variant: StatusVariant;
  label: string;
  /** Short line explaining what the status means for the provider. */
  hint: string;
}

/** Maps a policy's workflow status to its pill styling and plain-language copy. */
export const POLICY_STATUS_META: Record<PolicyStatus, StatusMeta> = {
  DRAFT: {
    variant: "info",
    label: "Draft",
    hint: "Only you can see this. Submit it for review to go live.",
  },
  PENDING: {
    variant: "pending",
    label: "In review",
    hint: "Our team is reviewing this plan. It is not public yet.",
  },
  APPROVED: {
    variant: "active",
    label: "Live",
    hint: "This plan is visible on the marketplace.",
  },
  INACTIVE: {
    variant: "expired",
    label: "Inactive",
    hint: "This plan has been taken down. Submit it again to relist.",
  },
};
