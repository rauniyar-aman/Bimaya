import Link from "next/link";
import { AddToCompare } from "@/components/marketplace/add-to-compare";
import { CategoryIcon } from "@/components/marketplace/category-icon";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { ArrowRightIcon } from "@/components/icons";
import { formatNpr, formatTerm, frequencySuffix } from "@/lib/format";
import type { PolicySummary } from "@/lib/api";

/** A single policy tile used across the marketplace and category pages. */
export function PolicyCard({ policy }: { policy: PolicySummary }) {
  return (
    <Card className="group flex flex-col p-5 transition-all hover:-translate-y-1 hover:border-brand-200 hover:shadow-md">
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
            <CategoryIcon iconKey={policy.category.icon} className="h-4 w-4" />
          </span>
          <Badge>{policy.category.name}</Badge>
        </span>
        {policy.is_featured && <StatusPill status="info">Featured</StatusPill>}
      </div>

      <h3 className="mt-4 font-display text-lg font-semibold leading-snug text-ink">
        {policy.name}
      </h3>
      <p className="mt-1 text-xs font-medium text-muted">
        {policy.provider.company_name}
      </p>
      <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-muted">
        {policy.summary || " "}
      </p>

      <div className="mt-4 grid grid-cols-2 gap-3 rounded-xl bg-surface p-3">
        <div>
          <p className="text-xs text-muted">Coverage</p>
          <p className="font-display text-sm font-semibold text-ink">
            {formatNpr(policy.coverage_amount)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted">Term</p>
          <p className="font-display text-sm font-semibold text-ink">
            {formatTerm(policy.term_months)}
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-end justify-between">
        <div>
          <p className="text-xs text-muted">Premium</p>
          <p className="font-display text-xl font-bold text-brand-600">
            {formatNpr(policy.premium)}
            <span className="text-xs font-medium text-muted">
              {frequencySuffix(policy.premium_frequency)}
            </span>
          </p>
        </div>
        <Link
          href={`/policies/${policy.slug}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 transition-colors hover:text-brand-700"
        >
          View plan
          <ArrowRightIcon className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>

      <div className="mt-3 border-t border-line pt-3">
        <AddToCompare policyId={policy.id} compact />
      </div>
    </Card>
  );
}
