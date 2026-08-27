import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AddToCompare } from "@/components/marketplace/add-to-compare";
import { CategoryIcon } from "@/components/marketplace/category-icon";
import { CompareBar } from "@/components/marketplace/compare-bar";
import { Container } from "@/components/layout/container";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusPill } from "@/components/ui/status-pill";
import { ArrowRightIcon, BadgeCheckIcon, CheckIcon } from "@/components/icons";
import { ApiError, api, type Policy } from "@/lib/api";
import { formatFrequency, formatNpr, formatTerm } from "@/lib/format";

type Params = Promise<{ slug: string }>;

async function loadPolicy(slug: string): Promise<Policy> {
  try {
    return await api.policies.get(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const { slug } = await params;
  try {
    const policy = await api.policies.get(slug);
    return {
      title: policy.name,
      description:
        policy.summary || `${policy.name} from ${policy.provider.company_name}.`,
    };
  } catch {
    return { title: "Policy" };
  }
}

function ageRange(policy: Policy): string {
  if (policy.min_age != null && policy.max_age != null)
    return `${policy.min_age}–${policy.max_age} years`;
  if (policy.min_age != null) return `${policy.min_age}+ years`;
  if (policy.max_age != null) return `Up to ${policy.max_age} years`;
  return "Any age";
}

export default async function PolicyDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  const policy = await loadPolicy(slug);

  return (
    <>
      <Navbar />
      <main className="flex-1">
        <Container className="py-8 lg:py-12">
          <nav className="text-sm text-muted" aria-label="Breadcrumb">
            <Link href="/policies" className="hover:text-brand-600">
              Policies
            </Link>
            <span className="mx-1.5">/</span>
            <Link
              href={`/categories/${policy.category.slug}`}
              className="hover:text-brand-600"
            >
              {policy.category.name}
            </Link>
          </nav>

          <div className="mt-6 grid gap-8 lg:grid-cols-3">
            {/* Details */}
            <div className="lg:col-span-2">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <CategoryIcon iconKey={policy.category.icon} className="h-5 w-5" />
                </span>
                <Badge>{policy.category.name}</Badge>
                {policy.is_featured && (
                  <StatusPill status="info">Featured</StatusPill>
                )}
              </div>

              <h1 className="mt-4 font-display text-3xl font-bold tracking-tight text-ink">
                {policy.name}
              </h1>
              <p className="mt-1.5 flex items-center gap-1.5 text-sm font-medium text-muted">
                <BadgeCheckIcon className="h-4 w-4 text-brand-500" />
                {policy.provider.company_name}
              </p>

              {policy.summary && (
                <p className="mt-4 text-lg leading-relaxed text-ink/80">
                  {policy.summary}
                </p>
              )}

              {policy.description && (
                <div className="mt-6">
                  <h2 className="font-display text-lg font-semibold text-ink">
                    About this plan
                  </h2>
                  <p className="mt-2 whitespace-pre-line leading-relaxed text-muted">
                    {policy.description}
                  </p>
                </div>
              )}

              {policy.features.length > 0 && (
                <div className="mt-6">
                  <h2 className="font-display text-lg font-semibold text-ink">
                    What&apos;s covered
                  </h2>
                  <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                    {policy.features.map((feature, i) => (
                      <li key={i} className="flex gap-2 text-sm text-ink">
                        <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-success-500" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {policy.add_ons.length > 0 && (
                <div className="mt-6">
                  <h2 className="font-display text-lg font-semibold text-ink">
                    Optional add-ons
                  </h2>
                  <ul className="mt-3 flex flex-wrap gap-2">
                    {policy.add_ons.map((addon, i) => (
                      <li
                        key={i}
                        className="rounded-full border border-line bg-surface px-3 py-1 text-sm text-ink"
                      >
                        {addon}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {policy.terms && (
                <div className="mt-6">
                  <h2 className="font-display text-lg font-semibold text-ink">
                    Terms &amp; conditions
                  </h2>
                  <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-muted">
                    {policy.terms}
                  </p>
                </div>
              )}
            </div>

            {/* Purchase card */}
            <div className="lg:col-span-1">
              <Card className="lg:sticky lg:top-24">
                <CardContent className="space-y-5">
                  <div>
                    <p className="text-xs text-muted">Premium</p>
                    <p className="font-display text-3xl font-bold text-brand-600">
                      {formatNpr(policy.premium)}
                    </p>
                    <p className="text-sm text-muted">
                      {formatFrequency(policy.premium_frequency)}
                    </p>
                  </div>

                  <dl className="grid grid-cols-2 gap-4 rounded-xl bg-surface p-4 text-sm">
                    <div>
                      <dt className="text-xs text-muted">Coverage</dt>
                      <dd className="font-display font-semibold text-ink">
                        {formatNpr(policy.coverage_amount)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted">Term</dt>
                      <dd className="font-display font-semibold text-ink">
                        {formatTerm(policy.term_months)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted">Eligible age</dt>
                      <dd className="font-display font-semibold text-ink">
                        {ageRange(policy)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-muted">Provider</dt>
                      <dd className="truncate font-display font-semibold text-ink">
                        {policy.provider.company_name}
                      </dd>
                    </div>
                  </dl>

                  <Link
                    href={`/checkout/${policy.slug}`}
                    className={buttonVariants({
                      variant: "cta",
                      size: "lg",
                      className: "w-full",
                    })}
                  >
                    Get this plan
                    <ArrowRightIcon className="h-4 w-4" />
                  </Link>

                  <AddToCompare policyId={policy.id} />

                  {policy.provider.website && (
                    <a
                      href={policy.provider.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-center text-sm font-medium text-brand-600 underline-offset-4 hover:underline"
                    >
                      Visit {policy.provider.company_name}
                    </a>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </Container>
      </main>
      <Footer />
      <CompareBar />
    </>
  );
}
