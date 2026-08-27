"use client";

import Link from "next/link";
import { use, useEffect, useState, useSyncExternalStore } from "react";
import { CompareTable } from "@/components/marketplace/compare-table";
import {
  clearCompare,
  getCompareIds,
  onCompareChange,
  removeCompareId,
  setCompareIds,
} from "@/components/marketplace/compare-store";
import { Container } from "@/components/layout/container";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CompareIcon } from "@/components/icons";
import { api, type PolicyCompare } from "@/lib/api";

type SearchParams = Promise<{ ids?: string | string[] }>;

function parseIds(raw: string | string[] | undefined): number[] {
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (!value) return [];
  const ids = value
    .split(",")
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isInteger(n) && n > 0);
  return Array.from(new Set(ids)).slice(0, 4);
}

export default function ComparePage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const sp = use(searchParams);

  // A `?ids=` link takes precedence; otherwise fall back to whatever the
  // visitor has selected around the site (kept in localStorage).
  const [override, setOverride] = useState<number[] | null>(() => {
    const fromUrl = parseIds(sp.ids);
    return fromUrl.length ? fromUrl : null;
  });
  const storeSnapshot = useSyncExternalStore(
    onCompareChange,
    () => getCompareIds().join(","),
    () => "",
  );
  const storeIds = storeSnapshot
    ? storeSnapshot.split(",").map(Number)
    : [];
  const ids = override ?? storeIds;
  const idsKey = ids.join(",");

  const [result, setResult] = useState<{
    key: string;
    data?: PolicyCompare[];
    error?: boolean;
  }>({ key: "" });

  useEffect(() => {
    if (ids.length === 0) return;
    // Sync a shared link into the store so compare buttons elsewhere match.
    if (override) setCompareIds(override);

    let cancelled = false;
    api.policies
      .compare(ids)
      .then((data) => {
        if (!cancelled) setResult({ key: idsKey, data });
      })
      .catch(() => {
        if (!cancelled) setResult({ key: idsKey, error: true });
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, override]);

  function handleRemove(id: number) {
    removeCompareId(id);
    if (override) setOverride(override.filter((v) => v !== id));
  }

  function handleClear() {
    clearCompare();
    setOverride([]);
  }

  const loading = ids.length > 0 && result.key !== idsKey;
  const errored = result.key === idsKey && Boolean(result.error);
  const policies = result.key === idsKey ? result.data ?? [] : [];

  return (
    <>
      <Navbar />
      <main className="flex-1">
        <Container className="py-8 lg:py-12">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
                Compare plans
              </h1>
              <p className="mt-2 text-muted">
                Line up premiums, coverage and features side by side.
              </p>
            </div>
            {ids.length > 0 && (
              <button
                type="button"
                onClick={handleClear}
                className="text-sm font-medium text-muted underline-offset-4 hover:text-ink hover:underline"
              >
                Clear all
              </button>
            )}
          </div>

          <div className="mt-8">
            {ids.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
                <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-500">
                  <CompareIcon className="h-6 w-6" />
                </span>
                <h2 className="mt-4 font-display text-lg font-semibold text-ink">
                  Nothing to compare yet
                </h2>
                <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
                  Browse the marketplace and add plans to compare them here.
                </p>
                <Link
                  href="/policies"
                  className={buttonVariants({
                    variant: "cta",
                    size: "md",
                    className: "mt-5",
                  })}
                >
                  Browse policies
                </Link>
              </div>
            ) : loading ? (
              <div className="flex items-center justify-center py-20">
                <Spinner className="h-6 w-6 text-brand-500" />
              </div>
            ) : errored ? (
              <Alert variant="error">
                We could not load the comparison. Please try again shortly.
              </Alert>
            ) : policies.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
                <h2 className="font-display text-lg font-semibold text-ink">
                  These plans are no longer available
                </h2>
                <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
                  They may have been withdrawn. Browse the marketplace for current
                  plans.
                </p>
                <Link
                  href="/policies"
                  className={buttonVariants({
                    variant: "secondary",
                    size: "md",
                    className: "mt-5",
                  })}
                >
                  Browse policies
                </Link>
              </div>
            ) : (
              <>
                <CompareTable policies={policies} onRemove={handleRemove} />
                <div className="mt-6">
                  <Link
                    href="/policies"
                    className="text-sm font-medium text-brand-600 underline-offset-4 hover:underline"
                  >
                    + Add more plans
                  </Link>
                </div>
              </>
            )}
          </div>
        </Container>
      </main>
      <Footer />
    </>
  );
}
