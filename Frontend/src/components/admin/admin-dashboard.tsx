"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { AnalyticsPanel } from "@/components/analytics/analytics-panel";
import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { StatCard, type StatTone } from "@/components/ui/stat-card";
import { BadgeCheckIcon, BuildingIcon, ClipboardIcon } from "@/components/icons";
import { api, type AdminAnalytics } from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; analytics: AdminAnalytics };

/**
 * Admin landing: the queues that need action right now, followed by the shared
 * analytics panel (totals, monthly trend, breakdowns). A single call to the
 * analytics endpoint backs both — the queue counts come from `analytics.queues`.
 */
export function AdminDashboard() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    api.admin
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
        We could not load the admin overview. Please refresh and try again.
      </Alert>
    );
  }

  const { queues } = state.analytics;

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold text-ink">Needs attention</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <QueueCard
            href="/admin/providers"
            label="Providers awaiting approval"
            count={queues.pending_providers}
            icon={<BuildingIcon className="h-5 w-5" />}
          />
          <QueueCard
            href="/admin/kyc"
            label="KYC pending review"
            count={queues.pending_kyc}
            icon={<BadgeCheckIcon className="h-5 w-5" />}
          />
          <QueueCard
            href="/admin/purchases"
            label="Payments to verify & forward"
            count={queues.paid_purchases}
            icon={<ClipboardIcon className="h-5 w-5" />}
          />
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-lg font-semibold text-ink">Overview</h2>
        <AnalyticsPanel data={state.analytics} />
      </section>
    </div>
  );
}

function QueueCard({
  href,
  label,
  count,
  icon,
}: {
  href: string;
  label: string;
  count: number;
  icon: React.ReactNode;
}) {
  const waiting = count > 0;
  const tone: StatTone = waiting ? "accent" : "success";
  return (
    <Link href={href} className="block">
      <StatCard
        label={label}
        value={count}
        hint={waiting ? "Tap to review →" : "All clear"}
        tone={tone}
        icon={icon}
        className="transition hover:border-brand-200 hover:shadow-sm"
      />
    </Link>
  );
}
