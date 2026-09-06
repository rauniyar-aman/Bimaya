"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Container } from "@/components/layout/container";
import { PurchaseRow } from "@/components/purchases/purchase-row";
import { RenewalBanner } from "@/components/purchases/renewal-banner";
import { ShieldCheckIcon } from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { api, type PolicyPurchase } from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; purchases: PolicyPurchase[] };

export function MyPolicies() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.purchases
      .list(authFetch)
      .then((page) => {
        if (!cancelled) setState({ phase: "ready", purchases: page.results });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  return (
    <Container className="flex-1 py-10 lg:py-14">
      <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        My policies
      </h1>
      <p className="mt-1.5 text-sm text-muted">
        Every policy you have bought through Bimaya, with its status and renewal dates.
      </p>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-8">
          We could not load your policies. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" &&
        (state.purchases.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="mt-8">
            <RenewalBanner purchases={state.purchases} />
            <div className="space-y-3">
              {state.purchases.map((purchase) => (
                <PurchaseRow key={purchase.id} purchase={purchase} />
              ))}
            </div>
          </div>
        ))}
    </Container>
  );
}

function EmptyState() {
  return (
    <Card className="mt-8">
      <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-500">
          <ShieldCheckIcon className="h-6 w-6" />
        </span>
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">
            No policies yet
          </h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-muted">
            Once you buy cover through Bimaya it appears here, with renewal dates
            and downloadable documents.
          </p>
        </div>
        <Link
          href="/policies"
          className={buttonVariants({ variant: "cta", size: "md" })}
        >
          Find your first policy
        </Link>
      </CardContent>
    </Card>
  );
}
