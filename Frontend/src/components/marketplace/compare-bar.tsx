"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";
import { CompareIcon, XIcon } from "@/components/icons";
import {
  clearCompare,
  getCompareIds,
  onCompareChange,
} from "./compare-store";

/**
 * A floating bar that appears once the visitor has selected policies to
 * compare. It reads the selection from `localStorage` and links to `/compare`.
 */
export function CompareBar() {
  const count = useSyncExternalStore(
    onCompareChange,
    () => getCompareIds().length,
    () => 0,
  );

  if (count === 0) return null;

  return (
    <div className="fixed inset-x-0 bottom-4 z-40 flex justify-center px-4">
      <div className="flex items-center gap-3 rounded-full border border-line bg-white/95 px-4 py-2.5 shadow-lg backdrop-blur">
        <span className="text-sm font-medium text-ink">
          {count} {count === 1 ? "plan" : "plans"} selected
        </span>
        <Link
          href={`/compare?ids=${getCompareIds().join(",")}`}
          className="inline-flex items-center gap-1.5 rounded-full bg-brand-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
        >
          <CompareIcon className="h-4 w-4" />
          Compare
        </Link>
        <button
          type="button"
          onClick={clearCompare}
          aria-label="Clear comparison"
          className="inline-flex h-7 w-7 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-ink"
        >
          <XIcon className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
