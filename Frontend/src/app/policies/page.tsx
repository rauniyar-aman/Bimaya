import type { Metadata } from "next";
import Link from "next/link";
import { CompareBar } from "@/components/marketplace/compare-bar";
import { PolicyCard } from "@/components/marketplace/policy-card";
import { PolicyFilters } from "@/components/marketplace/policy-filters";
import { Container } from "@/components/layout/container";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { api, type InsuranceCategory, type Paginated, type PolicySummary } from "@/lib/api";

export const metadata: Metadata = {
  title: "Browse policies",
  description:
    "Compare Life, Health, Vehicle and Travel insurance plans from trusted providers across Nepal.",
};

const PAGE_SIZE = 12;

type SearchParams = Promise<{ [key: string]: string | string[] | undefined }>;

function first(value: string | string[] | undefined): string | undefined {
  const v = Array.isArray(value) ? value[0] : value;
  return v && v.trim() ? v : undefined;
}

export default async function PoliciesPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const sp = await searchParams;
  const current = {
    search: first(sp.search),
    category: first(sp.category),
    ordering: first(sp.ordering),
    premium_max: first(sp.premium_max),
  };
  const pageNum = Math.max(1, Math.floor(Number(first(sp.page) ?? "1")) || 1);

  let data: Paginated<PolicySummary> | null = null;
  let categories: InsuranceCategory[] = [];
  let failed = false;
  try {
    [data, categories] = await Promise.all([
      api.policies.list({ ...current, page: pageNum }),
      api.categories.list(),
    ]);
  } catch {
    failed = true;
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  function pageHref(page: number): string {
    const params = new URLSearchParams();
    if (current.search) params.set("search", current.search);
    if (current.category) params.set("category", current.category);
    if (current.ordering) params.set("ordering", current.ordering);
    if (current.premium_max) params.set("premium_max", current.premium_max);
    if (page > 1) params.set("page", String(page));
    const qs = params.toString();
    return qs ? `/policies?${qs}` : "/policies";
  }

  return (
    <>
      <Navbar />
      <main className="flex-1">
        <section className="border-b border-line bg-gradient-to-b from-brand-50/60 to-white">
          <Container className="py-10 lg:py-14">
            <h1 className="font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
              Browse insurance plans
            </h1>
            <p className="mt-2 max-w-2xl text-muted">
              Compare Life, Health, Vehicle and Travel cover from licensed Nepali
              insurers. Filter by category, premium and coverage to find your fit.
            </p>
          </Container>
        </section>

        <Container className="py-8">
          <PolicyFilters categories={categories} current={current} />

          {failed || !data ? (
            <Alert variant="error" className="mt-8">
              We could not load policies right now. Please refresh the page or try
              again shortly.
            </Alert>
          ) : data.results.length === 0 ? (
            <div className="mt-10 rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
              <h2 className="font-display text-lg font-semibold text-ink">
                No policies match your filters
              </h2>
              <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
                Try widening your premium range or clearing the category filter.
              </p>
              <Link
                href="/policies"
                className={buttonVariants({
                  variant: "secondary",
                  size: "md",
                  className: "mt-5",
                })}
              >
                Clear filters
              </Link>
            </div>
          ) : (
            <>
              <p className="mt-6 text-sm text-muted">
                {data.count} {data.count === 1 ? "plan" : "plans"} available
              </p>
              <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {data.results.map((policy) => (
                  <PolicyCard key={policy.id} policy={policy} />
                ))}
              </div>

              {totalPages > 1 && (
                <nav
                  className="mt-10 flex items-center justify-center gap-2"
                  aria-label="Pagination"
                >
                  {pageNum > 1 && (
                    <Link
                      href={pageHref(pageNum - 1)}
                      className={buttonVariants({ variant: "secondary", size: "sm" })}
                    >
                      Previous
                    </Link>
                  )}
                  <span className="px-3 text-sm text-muted">
                    Page {pageNum} of {totalPages}
                  </span>
                  {pageNum < totalPages && (
                    <Link
                      href={pageHref(pageNum + 1)}
                      className={buttonVariants({ variant: "secondary", size: "sm" })}
                    >
                      Next
                    </Link>
                  )}
                </nav>
              )}
            </>
          )}
        </Container>
      </main>
      <Footer />
      <CompareBar />
    </>
  );
}
