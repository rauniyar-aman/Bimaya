"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { SearchIcon } from "@/components/icons";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { InsuranceCategory } from "@/lib/api";

const SORT_OPTIONS = [
  { value: "", label: "Featured first" },
  { value: "premium", label: "Premium: low to high" },
  { value: "-premium", label: "Premium: high to low" },
  { value: "-coverage_amount", label: "Coverage: high to low" },
  { value: "-created_at", label: "Newest" },
];

const PREMIUM_OPTIONS = [
  { value: "", label: "Any premium" },
  { value: "5000", label: "Under Rs 5,000" },
  { value: "15000", label: "Under Rs 15,000" },
  { value: "30000", label: "Under Rs 30,000" },
  { value: "60000", label: "Under Rs 60,000" },
];

export interface PolicyFilterValues {
  search?: string;
  category?: string;
  ordering?: string;
  premium_max?: string;
}

export function PolicyFilters({
  categories,
  current,
}: {
  categories: InsuranceCategory[];
  current: PolicyFilterValues;
}) {
  const router = useRouter();
  const [search, setSearch] = useState(current.search ?? "");

  const hasFilters = Boolean(
    current.search || current.category || current.ordering || current.premium_max,
  );

  // Rebuild the query from the current applied values plus this change, and
  // drop the page so results start from the first page again.
  function apply(overrides: PolicyFilterValues) {
    const merged = { ...current, search, ...overrides };
    const params = new URLSearchParams();
    if (merged.search) params.set("search", merged.search);
    if (merged.category) params.set("category", merged.category);
    if (merged.ordering) params.set("ordering", merged.ordering);
    if (merged.premium_max) params.set("premium_max", merged.premium_max);
    const qs = params.toString();
    router.push(qs ? `/policies?${qs}` : "/policies");
  }

  function clearAll() {
    setSearch("");
    router.push("/policies");
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        apply({});
      }}
      className="grid gap-3 rounded-2xl border border-line bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4"
      role="search"
      aria-label="Filter policies"
    >
      <div className="relative sm:col-span-2 lg:col-span-1">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <Input
          type="search"
          placeholder="Search policies…"
          aria-label="Search policies"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      <Select
        aria-label="Category"
        value={current.category ?? ""}
        onChange={(e) => apply({ category: e.target.value })}
      >
        <option value="">All categories</option>
        {categories.map((c) => (
          <option key={c.slug} value={c.slug}>
            {c.name}
          </option>
        ))}
      </Select>

      <Select
        aria-label="Maximum premium"
        value={current.premium_max ?? ""}
        onChange={(e) => apply({ premium_max: e.target.value })}
      >
        {PREMIUM_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>

      <Select
        aria-label="Sort by"
        value={current.ordering ?? ""}
        onChange={(e) => apply({ ordering: e.target.value })}
      >
        {SORT_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </Select>

      <div className="flex items-center gap-3 sm:col-span-2 lg:col-span-4">
        <button
          type="submit"
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-medium text-white transition-colors hover:bg-brand-700"
        >
          <SearchIcon className="h-4 w-4" />
          Search
        </button>
        {hasFilters && (
          <button
            type="button"
            onClick={clearAll}
            className="text-sm font-medium text-muted underline-offset-4 hover:text-ink hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>
    </form>
  );
}
