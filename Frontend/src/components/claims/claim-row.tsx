import Link from "next/link";
import { StatusPill } from "@/components/ui/status-pill";
import { CLAIM_STATUS_META } from "@/components/claims/claim-status";
import { formatNpr } from "@/lib/format";
import { formatDate } from "@/lib/date";
import type { Claim } from "@/lib/api";

/** One claim, shown on the My Claims list. Links to the claim detail page. */
export function ClaimRow({ claim }: { claim: Claim }) {
  const meta = CLAIM_STATUS_META[claim.status];
  const { policy } = claim.purchase;

  return (
    <Link
      href={`/dashboard/claims/${claim.id}`}
      className="block rounded-xl border border-line bg-card p-4 transition-colors hover:border-brand-200 hover:bg-surface/50 sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display font-semibold text-ink">{policy.name}</h3>
            <StatusPill status={meta.variant}>{meta.label}</StatusPill>
          </div>
          <p className="mt-1 text-sm text-muted">
            {policy.provider.company_name} · Claimed{" "}
            {formatNpr(claim.claimed_amount)} · Incident{" "}
            {formatDate(claim.incident_date)}
          </p>
        </div>
        <span aria-hidden="true" className="text-muted">
          →
        </span>
      </div>

      {claim.status === "SETTLED" && claim.approved_amount && (
        <p className="mt-2 text-xs text-muted">
          Settled for{" "}
          <span className="font-medium text-ink">
            {formatNpr(claim.approved_amount)}
          </span>
        </p>
      )}
    </Link>
  );
}
