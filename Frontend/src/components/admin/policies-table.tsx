"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { POLICY_FILTERS } from "@/components/admin/filters";
import { POLICY_STATUS_META } from "@/components/admin/status-meta";
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
  type AdminPolicy,
  type Paginated,
  type PolicyStatus,
} from "@/lib/api";
import { formatNpr } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<AdminPolicy> };

const FREQUENCY_LABELS: Record<string, string> = {
  MONTHLY: "/mo",
  QUARTERLY: "/qtr",
  YEARLY: "/yr",
  ONE_TIME: " one-time",
};

/** Admin read-only table of every policy across providers. */
export function PoliciesTable() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listPolicies(authFetch, {
        page,
        status: (status || undefined) as PolicyStatus | undefined,
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
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-display text-xl font-semibold text-ink">Policies</h2>
        <div className="flex gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search policy or provider"
              className="w-60 pl-9"
              aria-label="Search policies"
            />
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
            {POLICY_FILTERS.map((o) => (
              <option key={o.label} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {state.phase === "loading" && (
        <div className="flex items-center justify-center py-16">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {state.phase === "error" && (
        <Alert variant="error">
          We could not load policies. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
          No policies match your filters.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <>
          <Table>
            <THead>
              <TR>
                <TH>Policy</TH>
                <TH>Provider</TH>
                <TH className="text-right">Premium</TH>
                <TH className="text-right">Coverage</TH>
                <TH>Status</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((policy) => {
                const meta = POLICY_STATUS_META[policy.status];
                return (
                  <TR key={policy.id}>
                    <TD>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-ink">{policy.name}</span>
                        {policy.is_featured && (
                          <span className="rounded-full bg-accent-50 px-2 py-0.5 text-[11px] font-medium text-accent-700">
                            Featured
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted">{policy.category.name}</div>
                    </TD>
                    <TD className="text-muted">{policy.provider.company_name}</TD>
                    <TD className="text-right tabular-nums text-ink">
                      {formatNpr(policy.premium)}
                      <span className="text-xs text-muted">
                        {FREQUENCY_LABELS[policy.premium_frequency] ?? ""}
                      </span>
                    </TD>
                    <TD className="text-right tabular-nums text-ink">
                      {formatNpr(policy.coverage_amount)}
                    </TD>
                    <TD>
                      <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                    </TD>
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
