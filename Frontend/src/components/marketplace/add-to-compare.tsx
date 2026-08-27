"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";
import { CheckIcon, PlusIcon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import {
  MAX_COMPARE,
  getCompareIds,
  onCompareChange,
  toggleCompareId,
} from "./compare-store";

function useSelected(id: number): boolean {
  return useSyncExternalStore(
    onCompareChange,
    () => getCompareIds().includes(id),
    () => false,
  );
}

function useCompareCount(): number {
  return useSyncExternalStore(
    onCompareChange,
    () => getCompareIds().length,
    () => 0,
  );
}

/**
 * Toggles a policy in the compare selection (stored in `localStorage`).
 * `compact` renders a small chip for policy cards; the default renders a full
 * button plus a "compare now" link once two or more plans are selected.
 */
export function AddToCompare({
  policyId,
  compact = false,
}: {
  policyId: number;
  compact?: boolean;
}) {
  const selected = useSelected(policyId);
  const count = useCompareCount();
  const full = count >= MAX_COMPARE && !selected;

  if (compact) {
    return (
      <button
        type="button"
        onClick={() => toggleCompareId(policyId)}
        disabled={full}
        aria-pressed={selected}
        className={cn(
          "inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
          selected
            ? "border-brand-500 bg-brand-50 text-brand-700"
            : "border-line text-ink/70 hover:border-brand-200 hover:text-brand-600",
        )}
        title={full ? `Compare up to ${MAX_COMPARE} plans` : undefined}
      >
        {selected ? <CheckIcon className="h-3.5 w-3.5" /> : <PlusIcon className="h-3.5 w-3.5" />}
        {selected ? "Added" : "Compare"}
      </button>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button
        variant={selected ? "success" : "outline"}
        onClick={() => toggleCompareId(policyId)}
        disabled={full}
      >
        {selected ? <CheckIcon className="h-4 w-4" /> : <PlusIcon className="h-4 w-4" />}
        {selected ? "Added to compare" : "Add to compare"}
      </Button>
      {count >= 2 && (
        <Link
          href={`/compare?ids=${getCompareIds().join(",")}`}
          className="text-sm font-medium text-brand-600 underline-offset-4 hover:underline"
        >
          Compare {count} plans →
        </Link>
      )}
      {full && (
        <span className="text-xs text-muted">
          You can compare up to {MAX_COMPARE} plans.
        </span>
      )}
    </div>
  );
}
