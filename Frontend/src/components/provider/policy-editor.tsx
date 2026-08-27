"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { PolicyForm } from "@/components/provider/policy-form";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  ApiError,
  api,
  type InsuranceCategory,
  type ProviderPolicy,
} from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "notfound" }
  | { phase: "ready"; categories: InsuranceCategory[]; policy?: ProviderPolicy };

export function PolicyEditor({ policyId }: { policyId?: number }) {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.categories.list(),
      policyId != null
        ? api.provider.getPolicy(authFetch, policyId)
        : Promise.resolve(undefined),
    ])
      .then(([categories, policy]) => {
        if (!cancelled)
          setState({ phase: "ready", categories, policy: policy ?? undefined });
      })
      .catch((error) => {
        if (cancelled) return;
        // A policy id that is missing or not yours resolves to 404/403.
        if (
          policyId != null &&
          error instanceof ApiError &&
          (error.status === 404 || error.status === 403)
        ) {
          setState({ phase: "notfound" });
        } else {
          setState({ phase: "error" });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, policyId]);

  if (state.phase === "loading") {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner className="h-6 w-6 text-brand-500" />
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <Alert variant="error">
        We could not load this page. Please refresh and try again.
      </Alert>
    );
  }

  if (state.phase === "notfound") {
    return (
      <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
        <h2 className="font-display text-lg font-semibold text-ink">
          Policy not found
        </h2>
        <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
          This plan does not exist, or it is not one of yours.
        </p>
        <Link
          href="/provider"
          className={buttonVariants({
            variant: "secondary",
            size: "md",
            className: "mt-5",
          })}
        >
          Back to your policies
        </Link>
      </div>
    );
  }

  return <PolicyForm categories={state.categories} policy={state.policy} />;
}
