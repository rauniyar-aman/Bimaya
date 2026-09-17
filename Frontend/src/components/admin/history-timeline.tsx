"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill, type StatusVariant } from "@/components/ui/status-pill";
import {
  api,
  type AuthFetch,
  type HistoryEvent,
  type Paginated,
} from "@/lib/api";
import { formatDate, formatRelativeTime } from "@/lib/date";
import { formatNpr } from "@/lib/format";
import { cn } from "@/lib/cn";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<HistoryEvent> };

/** Short label for the coloured dot beside each event, keyed by category. */
const CATEGORY_LABELS: Record<string, string> = {
  account: "Account",
  kyc: "KYC",
  purchase: "Purchase",
  payment: "Payment",
  claim: "Claim",
  claim_message: "Message",
  provider: "Provider",
  provider_kyc: "Provider KYC",
  membership: "Team",
  policy: "Policy",
  payout: "Payout",
};

/**
 * A record's own lifecycle status ("ACTIVE", "MORE_INFO", "REJECTED", …) mapped
 * to a pill variant. The timeline spans purchases, claims, KYC, policies and
 * payouts, so this reads the shared vocabulary rather than one app's enum.
 */
const STATUS_VARIANTS: Record<string, StatusVariant> = {
  ACTIVE: "active",
  APPROVED: "active",
  VERIFIED: "active",
  PAID: "active",
  SETTLED: "success",
  SUCCESS: "success",
  PENDING: "pending",
  PENDING_PAYMENT: "pending",
  SUBMITTED: "info",
  UNDER_REVIEW: "info",
  FORWARDED: "info",
  MORE_INFO: "pending",
  REJECTED: "failed",
  CANCELLED: "failed",
  FAILED: "failed",
  INACTIVE: "failed",
  DRAFT: "expired",
  EXPIRED: "expired",
};

/** "MORE_INFO" → "More info". Used for statuses with no mapped label. */
function humanize(value: string): string {
  const words = value.replace(/_/g, " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function loadPage(
  authFetch: AuthFetch,
  subject: HistorySubject,
  id: number,
  page: number,
) {
  return subject === "user"
    ? api.admin.getUserHistory(authFetch, id, { page })
    : api.admin.getProviderHistory(authFetch, id, { page });
}

export type HistorySubject = "user" | "provider";

/**
 * The merged chronological history of one customer or provider: their own
 * activity (purchases, payments, claims, KYC, policies, team, payouts) and the
 * administrative actions taken on them, newest first. Each row is badged with
 * its source so an admin can tell "they did this" from "we did this".
 *
 * Admin rows are only returned to staff who also hold the audit-log permission
 * — the server decides that, so a timeline without them simply renders fewer
 * events.
 */
export function HistoryTimeline({
  subject,
  id,
}: {
  subject: HistorySubject;
  id: number;
}) {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);

  // The previous page stays on screen until the next one arrives, matching how
  // the admin tables page.
  useEffect(() => {
    let cancelled = false;
    loadPage(authFetch, subject, id, page)
      .then((data) => {
        if (!cancelled) setState({ phase: "ready", data });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, subject, id, page]);

  return (
    <Card>
      <CardContent className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-display text-lg font-semibold text-ink">History</h2>
          {state.phase === "ready" && (
            <p className="text-xs text-muted">
              {state.data.count} event{state.data.count === 1 ? "" : "s"}
            </p>
          )}
        </div>

        {state.phase === "loading" && (
          <div className="flex items-center justify-center py-12">
            <Spinner className="h-5 w-5 text-brand-500" />
          </div>
        )}

        {state.phase === "error" && (
          <Alert variant="error">
            We could not load this history. Please refresh and try again.
          </Alert>
        )}

        {state.phase === "ready" && state.data.results.length === 0 && (
          <p className="rounded-xl border border-dashed border-line bg-surface/50 p-8 text-center text-sm text-muted">
            Nothing has happened here yet.
          </p>
        )}

        {state.phase === "ready" && state.data.results.length > 0 && (
          <>
            <ol>
              {state.data.results.map((event, index) => (
                <TimelineRow
                  key={event.id}
                  event={event}
                  isLast={index === state.data.results.length - 1}
                />
              ))}
            </ol>
            <Pagination page={page} count={state.data.count} onChange={setPage} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

function TimelineRow({
  event,
  isLast,
}: {
  event: HistoryEvent;
  isLast: boolean;
}) {
  const isAdmin = event.source === "admin";
  const category = CATEGORY_LABELS[event.category] ?? humanize(event.category);

  return (
    <li className="relative pb-6 pl-7 last:pb-0">
      {/* The rail runs between dots, so the last row does not trail off. */}
      {!isLast && (
        <span
          aria-hidden="true"
          className="absolute bottom-0 left-[3px] top-4 w-px bg-line"
        />
      )}
      <span
        aria-hidden="true"
        className={cn(
          "absolute left-0 top-1.5 h-[7px] w-[7px] rounded-full",
          isAdmin ? "bg-accent-500" : "bg-brand-500",
        )}
      />

      <div className="flex flex-wrap items-center gap-2">
        <p className="font-medium text-ink">{event.title}</p>
        <Badge
          className={
            isAdmin ? "bg-accent-50 text-accent-700" : "bg-brand-50 text-brand-700"
          }
        >
          {isAdmin ? "Admin" : "Activity"}
        </Badge>
        {event.status && (
          <StatusPill status={STATUS_VARIANTS[event.status] ?? "info"}>
            {humanize(event.status)}
          </StatusPill>
        )}
      </div>

      <p className="mt-0.5 text-xs text-muted">
        {category} · {formatDate(event.timestamp)} ·{" "}
        {formatRelativeTime(event.timestamp)}
        {event.actor ? ` · ${event.actor}` : ""}
      </p>

      {event.detail && (
        <p className="mt-1.5 text-sm text-muted">{event.detail}</p>
      )}

      {event.amount !== null && (
        <p className="mt-1.5 text-sm font-medium tabular-nums text-ink">
          {formatNpr(event.amount)}
        </p>
      )}
    </li>
  );
}
