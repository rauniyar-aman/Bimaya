"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { PAYOUT_FILTERS } from "@/components/admin/filters";
import { PAYOUT_STATUS_META } from "@/components/admin/status-meta";
import { ExportButton } from "@/components/admin/export-button";
import { Alert } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { SearchIcon } from "@/components/icons";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  type AdminPayout,
  type Paginated,
  type PayoutStatus,
} from "@/lib/api";
import { formatDate } from "@/lib/date";
import { formatNpr } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<AdminPayout> };

/**
 * Read-only admin ledger of provider payouts — the commission Bimaya earns on
 * each issued sale and the net owed to the provider. Filterable by settlement
 * status, searchable by provider or policy, and exportable as CSV honouring the
 * active filters.
 */
export function PayoutsTable() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listPayouts(authFetch, {
        page,
        status: (statusFilter || undefined) as PayoutStatus | undefined,
        search: debouncedSearch || undefined,
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
  }, [authFetch, page, statusFilter, debouncedSearch]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-display text-xl font-semibold text-ink">Payouts</h2>
        <div className="flex gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search provider, policy, number"
              className="w-64 pl-9"
              aria-label="Search payouts"
            />
          </div>
          <Select
            value={statusFilter}
            onChange={(e) => {
              setPage(1);
              setStatusFilter(e.target.value);
            }}
            className="w-44"
            aria-label="Filter by status"
          >
            {PAYOUT_FILTERS.map((o) => (
              <option key={o.label} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          <ExportButton
            filename="bimaya-payouts.csv"
            onExport={() =>
              api.admin.exportPayouts(authFetch, {
                status: (statusFilter || undefined) as PayoutStatus | undefined,
                search: debouncedSearch || undefined,
              })
            }
          />
        </div>
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">
          We could not load payouts. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
          No payouts match your filters yet.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <>
          <Table>
            <THead>
              <TR>
                <TH>Provider</TH>
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
                    <TD className="font-medium text-ink">{payout.provider_name}</TD>
                    <TD>
                      <div className="text-ink">{payout.policy_name}</div>
                      {payout.policy_number && (
                        <div className="text-xs text-muted">
                          {payout.policy_number}
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
        </>
      )}
    </div>
  );
}
