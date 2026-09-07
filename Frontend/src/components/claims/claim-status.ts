import type { ClaimStatus } from "@/lib/api";
import type { StatusVariant } from "@/components/ui/status-pill";

interface StatusMeta {
  variant: StatusVariant;
  label: string;
  /** Short line explaining what the status means for the customer. */
  hint: string;
}

/** Maps a claim's lifecycle status to its pill styling and plain-language copy. */
export const CLAIM_STATUS_META: Record<ClaimStatus, StatusMeta> = {
  SUBMITTED: {
    variant: "info",
    label: "Submitted",
    hint: "Your claim is in the queue. The insurer will begin reviewing it shortly.",
  },
  UNDER_REVIEW: {
    variant: "info",
    label: "Under review",
    hint: "The insurer is reviewing your claim and the documents you provided.",
  },
  MORE_INFO: {
    variant: "pending",
    label: "More info needed",
    hint: "The insurer needs more from you. Add the requested details and resubmit.",
  },
  APPROVED: {
    variant: "active",
    label: "Approved",
    hint: "Your claim was approved. The payout is being processed.",
  },
  REJECTED: {
    variant: "failed",
    label: "Rejected",
    hint: "This claim was not approved. See the insurer's note for the reason.",
  },
  SETTLED: {
    variant: "success",
    label: "Settled",
    hint: "Your claim has been settled and the payout completed.",
  },
};
