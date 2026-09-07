"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { AnalyticsPanel } from "@/components/analytics/analytics-panel";
import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { api, type ProviderAnalytics } from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; analytics: ProviderAnalytics };

/** Analytics scoped to the provider's own book — totals, monthly trend, breakdowns. */
export function ProviderAnalyticsSection() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.provider
      .analytics(authFetch)
      .then((analytics) => {
        if (!cancelled) setState({ phase: "ready", analytics });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch]);

  return (
    <section>
      <h2 className="font-display text-xl font-semibold text-ink">Your analytics</h2>
      <p className="mt-1 text-sm text-muted">
        Purchases, premium collected and claims across the plans you list.
      </p>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-4">
          We could not load your analytics. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && (
        <div className="mt-4">
          <AnalyticsPanel data={state.analytics} />
        </div>
      )}
    </section>
  );
}
