"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { POLICY_FILTERS } from "@/components/admin/filters";
import { POLICY_STATUS_META } from "@/components/admin/status-meta";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { SearchIcon } from "@/components/icons";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  errorMessage,
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

type Action = "approve" | "reject" | "deactivate";
type Pending = { policy: AdminPolicy; action: Action };

const FREQUENCY_LABELS: Record<string, string> = {
  MONTHLY: "/mo",
  QUARTERLY: "/qtr",
  YEARLY: "/yr",
  ONE_TIME: " one-time",
};

const ACTION_COPY: Record<
  Action,
  { title: string; verb: string; variant: "success" | "primary" | "secondary" }
> = {
  approve: { title: "Approve policy", verb: "Approve", variant: "success" },
  reject: { title: "Send policy back", verb: "Send back", variant: "primary" },
  deactivate: { title: "Deactivate policy", verb: "Deactivate", variant: "secondary" },
};

/** Admin table of every policy across providers, with approve / reject / deactivate. */
export function PoliciesTable() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  const [pending, setPending] = useState<Pending | null>(null);
  const [working, setWorking] = useState(false);
  const [actionError, setActionError] = useState("");

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

  function updateRow(updated: AdminPolicy) {
    setState((prev) =>
      prev.phase === "ready"
        ? {
            phase: "ready",
            data: {
              ...prev.data,
              results: prev.data.results.map((p) =>
                p.id === updated.id ? updated : p,
              ),
            },
          }
        : prev,
    );
  }

  function ask(policy: AdminPolicy, action: Action) {
    setActionError("");
    setPending({ policy, action });
  }

  async function confirm() {
    if (!pending) return;
    setWorking(true);
    setActionError("");
    try {
      const { policy, action } = pending;
      const updated =
        action === "approve"
          ? await api.admin.approvePolicy(authFetch, policy.id)
          : action === "reject"
            ? await api.admin.rejectPolicy(authFetch, policy.id)
            : await api.admin.deactivatePolicy(authFetch, policy.id);
      updateRow(updated);
      setPending(null);
    } catch (error) {
      setActionError(errorMessage(error, "Could not update this policy."));
    } finally {
      setWorking(false);
    }
  }

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
                <TH className="text-right">Action</TH>
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
                    <TD className="text-right">
                      <PolicyActions policy={policy} onAction={ask} />
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>

          <Pagination page={page} count={state.data.count} onChange={setPage} />
        </>
      )}

      <Modal
        open={pending !== null}
        onClose={() => (working ? undefined : setPending(null))}
        title={pending ? ACTION_COPY[pending.action].title : ""}
      >
        {pending && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              {pending.action === "approve" && (
                <>
                  Approve{" "}
                  <strong className="text-ink">{pending.policy.name}</strong> by{" "}
                  {pending.policy.provider.company_name}? It goes live on the
                  marketplace and the provider is notified.
                </>
              )}
              {pending.action === "reject" && (
                <>
                  Send{" "}
                  <strong className="text-ink">{pending.policy.name}</strong> back to{" "}
                  {pending.policy.provider.company_name} for changes? It returns to
                  pending review and stops appearing publicly.
                </>
              )}
              {pending.action === "deactivate" && (
                <>
                  Deactivate{" "}
                  <strong className="text-ink">{pending.policy.name}</strong>? It is
                  removed from the marketplace until the provider resubmits it.
                </>
              )}
            </p>
            {actionError && <Alert variant="error">{actionError}</Alert>}
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setPending(null)}
                disabled={working}
              >
                Cancel
              </Button>
              <Button
                variant={ACTION_COPY[pending.action].variant}
                onClick={confirm}
                loading={working}
              >
                {ACTION_COPY[pending.action].verb}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

/** Status-driven action buttons for one policy row. */
function PolicyActions({
  policy,
  onAction,
}: {
  policy: AdminPolicy;
  onAction: (policy: AdminPolicy, action: Action) => void;
}) {
  if (policy.status === "PENDING") {
    return (
      <div className="flex justify-end gap-2">
        <Button variant="secondary" size="sm" onClick={() => onAction(policy, "reject")}>
          Send back
        </Button>
        <Button variant="success" size="sm" onClick={() => onAction(policy, "approve")}>
          Approve
        </Button>
      </div>
    );
  }
  if (policy.status === "APPROVED") {
    return (
      <Button variant="secondary" size="sm" onClick={() => onAction(policy, "deactivate")}>
        Deactivate
      </Button>
    );
  }
  if (policy.status === "INACTIVE") {
    return (
      <Button variant="success" size="sm" onClick={() => onAction(policy, "approve")}>
        Relist
      </Button>
    );
  }
  return <span className="text-xs text-muted">—</span>;
}
