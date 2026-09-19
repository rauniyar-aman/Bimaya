"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Container } from "@/components/layout/container";
import { ShieldCheckIcon } from "@/components/icons";
import { PURCHASE_STATUS_META } from "@/components/purchases/purchase-status";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { api, type PolicyPurchase } from "@/lib/api";
import { cn } from "@/lib/cn";
import { daysUntil, formatDate } from "@/lib/date";
import { formatNpr } from "@/lib/format";
import { firstName, homeForRole } from "@/lib/user";

/** How many policies the ledger shows before "View all". */
const PREVIEW_COUNT = 4;

/**
 * Cover ending within this many days needs the customer's attention. Matches
 * the window `RenewalBanner` uses, so the dashboard and the reminder agree on
 * what counts as "renewing soon".
 */
const RENEWAL_WINDOW_DAYS = 30;

/** Purchases that are paid for but not yet issued as cover. */
const IN_PROGRESS_STATUSES = ["PENDING_PAYMENT", "PAID", "FORWARDED"] as const;

type PoliciesState =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; purchases: PolicyPurchase[] };

/** An active policy with its term measured out in days. */
interface Runway {
  purchase: PolicyPurchase;
  /** Whole days until cover ends; negative once it has passed. */
  remaining: number | null;
  /** Length of the whole term in days, when both ends are known. */
  total: number | null;
}

function runwayFor(purchase: PolicyPurchase): Runway {
  const remaining = daysUntil(purchase.end_date);
  const sinceStart = daysUntil(purchase.start_date);
  const total =
    remaining !== null && sinceStart !== null ? remaining - sinceStart : null;
  return { purchase, remaining, total };
}

/** Active cover, soonest to expire first — what needs attention leads. */
function activeRunways(purchases: PolicyPurchase[]): Runway[] {
  return purchases
    .filter((purchase) => purchase.status === "ACTIVE")
    .map(runwayFor)
    .sort((a, b) => (a.remaining ?? Infinity) - (b.remaining ?? Infinity));
}

export function DashboardOverview() {
  const { user, authFetch } = useAuth();
  const router = useRouter();
  const [policies, setPolicies] = useState<PoliciesState>({ phase: "loading" });

  // This is the customer dashboard. Admins and providers have their own home
  // areas, so forward them there instead of showing an empty customer shell.
  const isCustomer = user?.role === "CUSTOMER";

  useEffect(() => {
    if (user && !isCustomer) router.replace(homeForRole(user.role));
  }, [user, isCustomer, router]);

  useEffect(() => {
    if (!isCustomer) return;
    let cancelled = false;
    api.purchases
      .list(authFetch)
      .then((page) => {
        if (!cancelled)
          setPolicies({ phase: "ready", purchases: page.results });
      })
      .catch(() => {
        if (!cancelled) setPolicies({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, isCustomer]);

  if (!user) return null;
  if (!isCustomer) {
    return (
      <Container className="flex flex-1 items-center justify-center py-24">
        <Spinner className="h-5 w-5 text-brand-500" />
      </Container>
    );
  }

  return (
    <Container className="flex-1 py-10 lg:py-14">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <p className="text-sm text-muted">Namaste, {firstName(user)}</p>
        <StatusPill status={user.is_verified ? "active" : "pending"}>
          {user.is_verified ? "Verified account" : "Verification pending"}
        </StatusPill>
      </div>

      {!user.is_verified && (
        <Alert variant="error" className="mt-5">
          Your account is not verified yet.{" "}
          <Link
            href={`/verify-otp?email=${encodeURIComponent(user.email)}`}
            className="font-medium underline underline-offset-4"
          >
            Enter your verification code
          </Link>{" "}
          to unlock purchases.
        </Alert>
      )}

      <PolicyLedger state={policies} />
    </Container>
  );
}

/** The customer's cover: what it totals, and how long each policy has left. */
function PolicyLedger({ state }: { state: PoliciesState }) {
  if (state.phase === "loading") {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="h-6 w-6 text-brand-500" />
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <Alert variant="error" className="mt-8">
        We could not load your policies. Refresh the page to try again.
      </Alert>
    );
  }

  if (state.purchases.length === 0) return <NoCoverYet />;

  const active = activeRunways(state.purchases);
  const inProgress = state.purchases.filter((purchase) =>
    IN_PROGRESS_STATUSES.some((status) => status === purchase.status),
  );

  const totalCover = active.reduce(
    (sum, { purchase }) => sum + Number(purchase.policy.coverage_amount ?? 0),
    0,
  );

  // The soonest expiry, but only once it is close enough to act on.
  const soonest = active[0];
  const renewing =
    soonest &&
    soonest.remaining !== null &&
    soonest.remaining >= 0 &&
    soonest.remaining <= RENEWAL_WINDOW_DAYS
      ? soonest
      : null;

  const shown = active.slice(0, PREVIEW_COUNT);

  return (
    <div className="mt-6">
      {/* Cover total — the figure the whole dashboard exists to report. It is
          sized fluidly because its length is the customer's, not ours: a
          seven-figure total must not run off the edge of a phone. */}
      <p className="font-display text-[clamp(1.875rem,8vw,3.75rem)] leading-none font-semibold tracking-tight text-ink tabular-nums">
        {formatNpr(totalCover)}
      </p>
      <p className="mt-3 max-w-xl text-muted">
        of cover in force across {active.length}{" "}
        {active.length === 1 ? "policy" : "policies"}.
        {renewing && (
          <>
            {" "}
            <span className="font-medium text-ink">
              {renewing.purchase.policy.name}
            </span>{" "}
            {expiryPhrase(renewing.remaining as number)}.
          </>
        )}
      </p>

      {renewing && (
        <Link
          href={`/dashboard/policies/${renewing.purchase.id}`}
          className={buttonVariants({ variant: "cta", className: "mt-5" })}
        >
          Renew this policy
        </Link>
      )}

      {active.length > 0 && (
        <ul className="mt-10 border-t border-line">
          {shown.map((runway) => (
            <RunwayRow key={runway.purchase.id} runway={runway} />
          ))}
        </ul>
      )}

      {active.length > PREVIEW_COUNT && (
        <Link
          href="/dashboard/policies"
          className="mt-5 inline-flex text-sm font-medium text-brand-ink underline-offset-4 hover:underline"
        >
          View all {active.length} policies
        </Link>
      )}

      {inProgress.length > 0 && <InProgress purchases={inProgress} />}
    </div>
  );
}

/** "renews in 24 days" / "renews tomorrow" / "ended 3 days ago". */
function expiryPhrase(days: number): string {
  if (days < 0) return "has ended";
  if (days === 0) return "renews today";
  if (days === 1) return "renews tomorrow";
  return `renews in ${days} days`;
}

/**
 * One active policy as a line in the ledger: what it covers, who carries it,
 * and a bar showing how much of the term is left to run.
 */
function RunwayRow({ runway }: { runway: Runway }) {
  const { purchase, remaining, total } = runway;
  const { policy } = purchase;

  const urgent = remaining !== null && remaining <= RENEWAL_WINDOW_DAYS;
  const lapsed = remaining !== null && remaining < 0;

  // How much of the term is still to run. Unknown dates leave the track empty
  // rather than guessing at a fraction.
  const left =
    remaining !== null && total !== null && total > 0
      ? Math.max(0, Math.min(1, remaining / total))
      : null;

  return (
    <li className="border-b border-line">
      <Link
        href={`/dashboard/policies/${purchase.id}`}
        className="group block py-5 transition-colors hover:bg-surface/60"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
          <h2 className="font-display text-xl font-semibold text-ink group-hover:text-brand-ink">
            {policy.name}
          </h2>
          <p className="font-display text-xl font-semibold text-ink tabular-nums">
            {formatNpr(policy.coverage_amount)}
          </p>
        </div>

        <div
          aria-hidden="true"
          className="mt-3 h-1 w-full overflow-hidden rounded-full bg-line"
        >
          {left !== null && (
            <div
              className={cn(
                "h-full rounded-full",
                lapsed
                  ? "bg-danger"
                  : urgent
                    ? "bg-accent-500"
                    : "bg-success-500",
              )}
              style={{ width: `${Math.max(left * 100, 2)}%` }}
            />
          )}
        </div>

        <div className="mt-2.5 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 text-sm">
          <p className="text-muted">{policy.provider.company_name}</p>
          <div className="flex items-baseline gap-5">
            {purchase.end_date && (
              <p className="hidden text-muted sm:block">
                Ends {formatDate(purchase.end_date)}
              </p>
            )}
            <p
              className={cn(
                "tabular-nums",
                lapsed
                  ? "text-danger"
                  : urgent
                    ? "font-medium text-accent-700 dark:text-accent-300"
                    : "text-muted",
              )}
            >
              {remaining === null
                ? "Term dates pending"
                : lapsed
                  ? "Cover ended"
                  : `${remaining} days left`}
            </p>
          </div>
        </div>
      </Link>
    </li>
  );
}

/** Purchases that are paid for but not yet cover, with the step each is on. */
function InProgress({ purchases }: { purchases: PolicyPurchase[] }) {
  return (
    <section className="mt-12">
      <h2 className="font-display text-lg font-semibold text-ink">
        Not yet in force
      </h2>
      <ul className="mt-4 border-t border-line">
        {purchases.map((purchase) => {
          const meta = PURCHASE_STATUS_META[purchase.status];
          return (
            <li key={purchase.id} className="border-b border-line">
              <Link
                href={`/dashboard/policies/${purchase.id}`}
                className="group flex flex-wrap items-center justify-between gap-x-6 gap-y-2 py-4 transition-colors hover:bg-surface/60"
              >
                <div>
                  <p className="font-display font-semibold text-ink group-hover:text-brand-ink">
                    {purchase.policy.name}
                  </p>
                  <p className="mt-0.5 text-sm text-muted">{meta.hint}</p>
                </div>
                <div className="flex items-center gap-4">
                  <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                  {purchase.status === "PENDING_PAYMENT" && (
                    <span className="text-sm font-medium text-accent-700 dark:text-accent-300">
                      Finish payment
                    </span>
                  )}
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** First run: no purchases at all. An empty screen is an invitation to act. */
function NoCoverYet() {
  return (
    <div className="mt-10 max-w-lg">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-500 dark:bg-brand-900">
        <ShieldCheckIcon className="h-6 w-6" />
      </span>
      <h2 className="mt-5 font-display text-3xl font-semibold tracking-tight text-ink">
        You have no cover yet
      </h2>
      <p className="mt-3 leading-relaxed text-muted">
        Buy a policy through Bimaya and it appears here — what it covers, how
        long it has left to run, and its documents ready to download.
      </p>
      <Link
        href="/policies"
        className={buttonVariants({ variant: "cta", size: "lg", className: "mt-6" })}
      >
        Find your first policy
      </Link>
    </div>
  );
}
