"use client";

import Link from "next/link";
import { CheckIcon, XIcon } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { formatFrequency, formatNpr, formatTerm } from "@/lib/format";
import type { PolicyCompare } from "@/lib/api";

function ageRange(policy: PolicyCompare): string {
  if (policy.min_age != null && policy.max_age != null)
    return `${policy.min_age}–${policy.max_age} yrs`;
  if (policy.min_age != null) return `${policy.min_age}+ yrs`;
  if (policy.max_age != null) return `Up to ${policy.max_age} yrs`;
  return "Any age";
}

function BulletList({ items }: { items: string[] }) {
  if (!items.length) return <span className="text-sm text-muted">—</span>;
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-1.5 text-sm text-ink">
          <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-success-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Side-by-side comparison of up to four policies. */
export function CompareTable({
  policies,
  onRemove,
}: {
  policies: PolicyCompare[];
  onRemove: (id: number) => void;
}) {
  const rows: { label: string; render: (p: PolicyCompare) => React.ReactNode }[] = [
    { label: "Provider", render: (p) => p.provider.company_name },
    {
      label: "Premium",
      render: (p) => (
        <span className="font-display font-semibold text-brand-600">
          {formatNpr(p.premium)}{" "}
          <span className="text-xs font-medium text-muted">
            {formatFrequency(p.premium_frequency)}
          </span>
        </span>
      ),
    },
    { label: "Coverage", render: (p) => formatNpr(p.coverage_amount) },
    { label: "Term", render: (p) => formatTerm(p.term_months) },
    { label: "Eligible age", render: (p) => ageRange(p) },
    { label: "Key features", render: (p) => <BulletList items={p.features} /> },
    { label: "Add-ons", render: (p) => <BulletList items={p.add_ons} /> },
  ];

  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-white shadow-sm">
      <table className="w-full min-w-[640px] border-collapse text-left align-top">
        <thead>
          <tr className="border-b border-line">
            <th className="w-40 p-4" />
            {policies.map((p) => (
              <th key={p.id} className="min-w-56 p-4 align-top">
                <div className="flex items-start justify-between gap-2">
                  <Badge>{p.category.name}</Badge>
                  <button
                    type="button"
                    onClick={() => onRemove(p.id)}
                    aria-label={`Remove ${p.name}`}
                    className="inline-flex h-6 w-6 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-ink"
                  >
                    <XIcon className="h-3.5 w-3.5" />
                  </button>
                </div>
                <Link
                  href={`/policies/${p.slug}`}
                  className="mt-2 block font-display text-base font-semibold leading-snug text-ink hover:text-brand-600"
                >
                  {p.name}
                </Link>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-b border-line last:border-0">
              <th
                scope="row"
                className="bg-surface/60 p-4 text-sm font-medium text-muted"
              >
                {row.label}
              </th>
              {policies.map((p) => (
                <td key={p.id} className="p-4 text-sm text-ink">
                  {row.render(p)}
                </td>
              ))}
            </tr>
          ))}
          <tr>
            <th scope="row" className="bg-surface/60 p-4" />
            {policies.map((p) => (
              <td key={p.id} className="p-4">
                <Link
                  href={`/checkout/${p.slug}`}
                  className={buttonVariants({ variant: "cta", size: "sm" })}
                >
                  Get this plan
                </Link>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
