"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill, type StatusVariant } from "@/components/ui/status-pill";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  type Paginated,
  type PayoutStatus,
  type ProviderPayout,
} from "@/lib/api";
import { formatDate } from "@/lib/date";
import { formatNpr } from "@/lib/format";

/** Status-pill variant + label for a payout's settlement state. */
const PAYOUT_STATUS_META: Record<
  PayoutStatus,
  { variant: StatusVariant; label: string }
> = {
  PENDING: { variant: "pending", label: "Pending" },
  PAID: { variant: "active", label: "Paid" },
};

const STATUS_FILTERS = [
  { value: "", label: "All payouts" },
  { value: "PENDING", label: "Pending" },
  { value: "PAID", label: "Paid" },
];

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<ProviderPayout> };

/**
 * Read-only payout ledger for the signed-in provider: what Bimaya owes on each
 * issued sale after commission, and whether it has been paid. Amounts and the
 * commission rate are snapshotted at issuance, so historical rows are stable
 * even if the provider's rate later changes.
 */
export function ProviderPayouts() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.provider
      .listPayouts(authFetch, {
        page,
        status: (status || undefined) as PayoutStatus | undefined,
      })
      .then((data) => {
        if (!cancelled) setState({ phase: "ready", data });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, page, status]);

  return (
    <section>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-xl font-semibold text-ink">Payouts</h2>
          <p className="mt-1 text-sm text-muted">
            What you&apos;re owed on each issued policy, net of platform commission.
          </p>
        </div>
        <Select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
          className="w-44"
          aria-label="Filter by status"
        >
          {STATUS_FILTERS.map((o) => (
            <option key={o.label} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-4">
          We could not load your payouts. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-surface/50 p-10 text-center text-sm text-muted">
          No payouts yet. They appear here once your issued policies go active.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <div className="mt-4 space-y-5">
          <Table>
            <THead>
              <TR>
                <TH>Policy</TH>
                <TH className="text-right">Gross</TH>
                <TH className="text-right">Commission</TH>
                <TH className="text-right">Net payable</TH>
                <TH>Status</TH>
                <TH>Issued</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((payout) => {
                const meta = PAYOUT_STATUS_META[payout.status];
                return (
                  <TR key={payout.id}>
                    <TD>
                      <div className="font-medium text-ink">
                        {payout.policy_name}
                      </div>
                      {payout.policy_number && (
                        <div className="text-xs text-muted">
                          No. {payout.policy_number}
                        </div>
                      )}
                    </TD>
                    <TD className="text-right tabular-nums text-ink">
                      {formatNpr(payout.gross_amount)}
                    </TD>
                    <TD className="text-right tabular-nums text-ink">
                      {formatNpr(payout.commission_amount)}
                      <div className="text-xs text-muted">
                        {payout.commission_rate}%
                      </div>
                    </TD>
                    <TD className="text-right tabular-nums font-medium text-ink">
                      {formatNpr(payout.net_amount)}
                    </TD>
                    <TD>
                      <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                      {payout.paid_at && (
                        <div className="mt-1 text-xs text-muted">
                          {formatDate(payout.paid_at)}
                        </div>
                      )}
                    </TD>
                    <TD className="text-muted">{formatDate(payout.created_at)}</TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>

          <Pagination page={page} count={state.data.count} onChange={setPage} />
        </div>
      )}
    </section>
  );
}
