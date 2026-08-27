"use client";

import Link from "next/link";
import { Suspense, use, useEffect, useState } from "react";
import { RequireAuth } from "@/components/auth/require-auth";
import { Container } from "@/components/layout/container";
import { Footer } from "@/components/layout/footer";
import { Navbar } from "@/components/layout/navbar";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { LockIcon, ShieldCheckIcon, WalletIcon } from "@/components/icons";
import { ApiError, api, type Policy } from "@/lib/api";
import { formatFrequency, formatNpr, formatTerm } from "@/lib/format";

type Params = Promise<{ slug: string }>;

type LoadState =
  | { status: "loading" }
  | { status: "ready"; policy: Policy }
  | { status: "notfound" }
  | { status: "error" };

function CheckoutInner({ slug }: { slug: string }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.policies
      .get(slug)
      .then((policy) => {
        if (!cancelled) setState({ status: "ready", policy });
      })
      .catch((error) => {
        if (cancelled) return;
        setState(
          error instanceof ApiError && error.status === 404
            ? { status: "notfound" }
            : { status: "error" },
        );
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (state.status === "loading") {
    return (
      <main className="flex flex-1 items-center justify-center py-24">
        <Spinner className="h-6 w-6 text-brand-500" />
      </main>
    );
  }

  if (state.status === "notfound" || state.status === "error") {
    return (
      <main className="flex-1">
        <Container className="py-16">
          <div className="mx-auto max-w-lg rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
            <h1 className="font-display text-xl font-semibold text-ink">
              {state.status === "notfound"
                ? "This plan is no longer available"
                : "Something went wrong"}
            </h1>
            <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
              {state.status === "notfound"
                ? "It may have been withdrawn. Browse the marketplace for current plans."
                : "We could not load this plan. Please try again shortly."}
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
        </Container>
      </main>
    );
  }

  const { policy } = state;

  return (
    <main className="flex-1">
      <Container className="py-8 lg:py-12">
        <Link
          href={`/policies/${policy.slug}`}
          className="text-sm font-medium text-muted underline-offset-4 hover:text-ink hover:underline"
        >
          ← Back to plan
        </Link>

        <h1 className="mt-4 font-display text-3xl font-bold tracking-tight text-ink">
          Checkout
        </h1>
        <p className="mt-1.5 text-muted">
          Review your plan and choose how to pay.
        </p>

        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          {/* Plan summary */}
          <div className="lg:col-span-2">
            <Card>
              <CardContent className="space-y-5">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted">
                    {policy.category.name}
                  </p>
                  <h2 className="mt-1 font-display text-xl font-semibold text-ink">
                    {policy.name}
                  </h2>
                  <p className="mt-1 text-sm text-muted">
                    by {policy.provider.company_name}
                  </p>
                </div>

                <dl className="grid grid-cols-2 gap-4 rounded-xl bg-surface p-4 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-xs text-muted">Premium</dt>
                    <dd className="font-display font-semibold text-ink">
                      {formatNpr(policy.premium)}
                      <span className="text-xs font-normal text-muted">
                        {" "}
                        · {formatFrequency(policy.premium_frequency)}
                      </span>
                    </dd>
                  </div>
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
                </dl>

                <div className="flex items-start gap-2 rounded-xl border border-line bg-white p-4 text-sm text-muted">
                  <ShieldCheckIcon className="mt-0.5 h-5 w-5 shrink-0 text-success-500" />
                  <p>
                    Your details are protected. You will confirm nominee and KYC
                    information before any payment is taken.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Payment (coming soon) */}
          <div className="lg:col-span-1">
            <Card className="lg:sticky lg:top-24">
              <CardContent className="space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted">Amount due</p>
                    <p className="font-display text-2xl font-bold text-brand-600">
                      {formatNpr(policy.premium)}
                    </p>
                  </div>
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-brand-500">
                    <WalletIcon className="h-5 w-5" />
                  </span>
                </div>

                <div className="rounded-xl border border-dashed border-line bg-surface/60 p-4 text-center">
                  <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-white text-brand-500 shadow-sm">
                    <LockIcon className="h-5 w-5" />
                  </span>
                  <p className="mt-3 text-sm font-semibold text-ink">
                    Secure checkout is coming soon
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    Online payment with eSewa and Khalti is on its way. You
                    won&apos;t be charged today.
                  </p>
                </div>

                <div className="space-y-2.5">
                  <button
                    type="button"
                    disabled
                    className="flex w-full cursor-not-allowed items-center justify-between rounded-xl border border-line bg-white px-4 py-3 text-sm font-medium text-ink/70 opacity-70"
                  >
                    Pay with eSewa
                    <span className="rounded-full bg-surface px-2 py-0.5 text-[11px] text-muted">
                      Soon
                    </span>
                  </button>
                  <button
                    type="button"
                    disabled
                    className="flex w-full cursor-not-allowed items-center justify-between rounded-xl border border-line bg-white px-4 py-3 text-sm font-medium text-ink/70 opacity-70"
                  >
                    Pay with Khalti
                    <span className="rounded-full bg-surface px-2 py-0.5 text-[11px] text-muted">
                      Soon
                    </span>
                  </button>
                </div>

                <Link
                  href={`/policies/${policy.slug}`}
                  className="block text-center text-sm font-medium text-brand-600 underline-offset-4 hover:underline"
                >
                  Back to plan details
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </Container>
    </main>
  );
}

export default function CheckoutPage({ params }: { params: Params }) {
  const { slug } = use(params);

  return (
    <>
      <Navbar />
      <Suspense
        fallback={
          <div className="flex flex-1 items-center justify-center py-24">
            <Spinner className="h-5 w-5 text-brand-500" />
          </div>
        }
      >
        <RequireAuth>
          <CheckoutInner slug={slug} />
        </RequireAuth>
      </Suspense>
      <Footer />
    </>
  );
}
