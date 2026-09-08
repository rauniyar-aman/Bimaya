"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Alert } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill, type StatusVariant } from "@/components/ui/status-pill";
import { SearchIcon } from "@/components/icons";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  type Paginated,
  type ProviderPurchase,
  type PurchaseStatus,
} from "@/lib/api";
import { formatDate } from "@/lib/date";
import { formatNpr } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

/** Status-pill variant + label for a purchase, from the provider's vantage. */
const PURCHASE_STATUS_META: Record<
  PurchaseStatus,
  { variant: StatusVariant; label: string }
> = {
  PENDING_PAYMENT: { variant: "pending", label: "Pending payment" },
  PAID: { variant: "info", label: "Paid — in review" },
  FORWARDED: { variant: "info", label: "Awaiting issuance" },
  ACTIVE: { variant: "active", label: "Active" },
  EXPIRED: { variant: "expired", label: "Expired" },
  CANCELLED: { variant: "failed", label: "Cancelled" },
};

const STATUS_FILTERS = [
  { value: "", label: "All purchases" },
  { value: "PENDING_PAYMENT", label: "Pending payment" },
  { value: "PAID", label: "Paid — in review" },
  { value: "FORWARDED", label: "Awaiting issuance" },
  { value: "ACTIVE", label: "Active" },
  { value: "EXPIRED", label: "Expired" },
  { value: "CANCELLED", label: "Cancelled" },
];

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<ProviderPurchase> };

/** Read-only sales history: every purchase on this provider's policies. */
export function ProviderSales() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  useEffect(() => {
    let cancelled = false;
    api.provider
      .listPurchases(authFetch, {
        page,
        status: (status || undefined) as PurchaseStatus | undefined,
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
  }, [authFetch, page, status, debouncedSearch]);

  return (
    <section>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-display text-xl font-semibold text-ink">Sales</h2>
          <p className="mt-1 text-sm text-muted">
            Every purchase customers have made on your policies.
          </p>
        </div>
        <div className="flex gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search policy or number"
              className="w-56 pl-9"
              aria-label="Search sales"
            />
          </div>
          <Select
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value);
            }}
            className="w-48"
            aria-label="Filter by status"
          >
            {STATUS_FILTERS.map((o) => (
              <option key={o.label} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-12">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error" className="mt-4">
          We could not load your sales. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="mt-4 rounded-2xl border border-dashed border-line bg-surface/50 p-10 text-center text-sm text-muted">
          No purchases match your filters yet.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <div className="mt-4 space-y-5">
          <Table>
            <THead>
              <TR>
                <TH>Policy</TH>
                <TH>Customer</TH>
                <TH className="text-right">Premium</TH>
                <TH>Status</TH>
                <TH>Purchased</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((purchase) => {
                const meta = PURCHASE_STATUS_META[purchase.status];
                return (
                  <TR key={purchase.id}>
                    <TD>
                      <div className="font-medium text-ink">
                        {purchase.policy.name}
                      </div>
                      <div className="text-xs text-muted">
                        {purchase.policy_number
                          ? `No. ${purchase.policy_number}`
                          : purchase.policy.category.name}
                      </div>
                    </TD>
                    <TD className="text-ink">{purchase.customer_name || "—"}</TD>
                    <TD className="text-right tabular-nums text-ink">
                      {formatNpr(purchase.policy.premium)}
                    </TD>
                    <TD>
                      <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                    </TD>
                    <TD className="text-muted">{formatDate(purchase.created_at)}</TD>
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
