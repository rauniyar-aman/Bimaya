"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { ClaimRow } from "@/components/claims/claim-row";
import { Container } from "@/components/layout/container";
import { ShieldCheckIcon } from "@/components/icons";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { api, type Claim } from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; claims: Claim[] };

export function MyClaims() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.claims
      .list(authFetch)
      .then((page) => {
        if (!cancelled) setState({ phase: "ready", claims: page.results });
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
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
            My claims
          </h1>
          <p className="mt-1.5 text-sm text-muted">
            Every claim you have filed, with its status and settlement details.
          </p>
        </div>
        <Link
          href="/dashboard/claims/new"
          className={buttonVariants({ variant: "cta", size: "md" })}
        >
          File a claim
        </Link>
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-8">
          We could not load your claims. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" &&
        (state.claims.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="mt-8 space-y-3">
            {state.claims.map((claim) => (
              <ClaimRow key={claim.id} claim={claim} />
            ))}
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
            No claims yet
          </h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-muted">
            If something happens to an active policy, file a claim here and track
            it from submission through to settlement.
          </p>
        </div>
        <Link
          href="/dashboard/claims/new"
          className={buttonVariants({ variant: "cta", size: "md" })}
        >
          File a claim
        </Link>
      </CardContent>
    </Card>
  );
}
