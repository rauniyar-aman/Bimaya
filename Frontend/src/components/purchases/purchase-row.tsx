import Link from "next/link";
import { StatusPill } from "@/components/ui/status-pill";
import { PURCHASE_STATUS_META } from "@/components/purchases/purchase-status";
import { formatFrequency, formatNpr, formatTerm } from "@/lib/format";
import { formatDate } from "@/lib/date";
import type { PolicyPurchase } from "@/lib/api";

/** One purchased policy, shown on the My Policies list and dashboard preview. */
export function PurchaseRow({ purchase }: { purchase: PolicyPurchase }) {
  const { policy } = purchase;
  const meta = PURCHASE_STATUS_META[purchase.status];

  return (
    <Link
      href={`/dashboard/policies/${purchase.id}`}
      className="block rounded-xl border border-line bg-card p-4 transition-colors hover:border-brand-200 hover:bg-surface/50 sm:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display font-semibold text-ink">{policy.name}</h3>
            <StatusPill status={meta.variant}>{meta.label}</StatusPill>
          </div>
          <p className="mt-1 text-sm text-muted">
            {policy.provider.company_name} · {formatNpr(policy.premium)}{" "}
            {formatFrequency(policy.premium_frequency)} ·{" "}
            {formatNpr(policy.coverage_amount)} cover · {formatTerm(policy.term_months)}
          </p>
        </div>
        <span aria-hidden="true" className="text-muted">
          →
        </span>
      </div>

      {purchase.status === "ACTIVE" && (
        <p className="mt-2 text-xs text-muted">
          Policy no. <span className="font-medium text-ink">{purchase.policy_number}</span>
          {purchase.start_date && purchase.end_date && (
            <>
              {" "}
              · {formatDate(purchase.start_date)} – {formatDate(purchase.end_date)}
            </>
          )}
        </p>
      )}
    </Link>
  );
}
