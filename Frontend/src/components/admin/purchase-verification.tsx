"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { PURCHASE_FILTERS } from "@/components/admin/filters";
import { KYC_STATUS_META, PURCHASE_STATUS_META } from "@/components/admin/status-meta";
import { ExportButton } from "@/components/admin/export-button";
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
  errorCode,
  errorMessage,
  type AdminPurchase,
  type Paginated,
  type PurchaseStatus,
} from "@/lib/api";
import { formatDate } from "@/lib/date";
import { formatNpr } from "@/lib/format";
import { useDebouncedValue } from "@/lib/use-debounced-value";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<AdminPurchase> };

/** Admin table of purchases with the verify-and-forward action on paid rows. */
export function PurchaseVerification() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  const [pending, setPending] = useState<AdminPurchase | null>(null);
  const [working, setWorking] = useState(false);
  const [actionError, setActionError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listPurchases(authFetch, {
        page,
        status: (statusFilter || undefined) as PurchaseStatus | undefined,
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

  function updateRow(updated: AdminPurchase) {
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

  async function confirm() {
    if (!pending) return;
    setWorking(true);
    setActionError("");
    try {
      const updated = await api.admin.verifyAndForwardPurchase(authFetch, pending.id);
      updateRow(updated);
      setPending(null);
    } catch (error) {
      // The backend guards this transition; surface its reason plainly.
      const code = errorCode(error);
      setActionError(
        code === "purchase_not_forwardable"
          ? errorMessage(error, "This purchase can't be forwarded yet.")
          : errorMessage(error, "Could not forward this purchase."),
      );
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-display text-xl font-semibold text-ink">Purchases</h2>
        <div className="flex gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search customer, policy, number"
              className="w-64 pl-9"
              aria-label="Search purchases"
            />
          </div>
          <Select
            value={statusFilter}
            onChange={(e) => {
              setPage(1);
              setStatusFilter(e.target.value);
            }}
            className="w-52"
            aria-label="Filter by status"
          >
            {PURCHASE_FILTERS.map((o) => (
              <option key={o.label} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          <ExportButton
            filename="bimaya-purchases.csv"
            onExport={() =>
              api.admin.exportPurchases(authFetch, {
                status: (statusFilter || undefined) as PurchaseStatus | undefined,
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
          We could not load purchases. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
          No purchases match your filters.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <>
          <Table>
            <THead>
              <TR>
                <TH>Customer</TH>
                <TH>Policy</TH>
                <TH>Insured / KYC</TH>
                <TH className="text-right">Premium</TH>
                <TH>Status</TH>
                <TH className="text-right">Action</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((purchase) => {
                const meta = PURCHASE_STATUS_META[purchase.status];
                const kyc = purchase.kyc;
                const kycMeta = kyc ? KYC_STATUS_META[kyc.status] : null;
                const canForward =
                  purchase.status === "PAID" && kyc?.status === "VERIFIED";
                return (
                  <TR key={purchase.id}>
                    <TD>
                      <div className="font-medium text-ink">
                        {purchase.customer_name || "—"}
                      </div>
                      <div className="text-xs text-muted">{purchase.customer_email}</div>
                    </TD>
                    <TD>
                      <div className="text-ink">{purchase.policy.name}</div>
                      <div className="text-xs text-muted">
                        {purchase.policy.provider.company_name}
                      </div>
                    </TD>
                    <TD>
                      <div className="text-ink">{kyc?.full_name ?? "—"}</div>
                      {kycMeta && (
                        <StatusPill status={kycMeta.variant} className="mt-1">
                          {kycMeta.label}
                        </StatusPill>
                      )}
                    </TD>
                    <TD className="text-right tabular-nums text-ink">
                      {formatNpr(purchase.policy.premium)}
                    </TD>
                    <TD>
                      <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                      {purchase.policy_number && (
                        <div className="mt-1 text-xs text-muted">
                          {purchase.policy_number}
                        </div>
                      )}
                    </TD>
                    <TD className="text-right">
                      {purchase.status === "PAID" ? (
                        <Button
                          variant="cta"
                          size="sm"
                          disabled={!canForward}
                          title={
                            canForward
                              ? undefined
                              : "The customer's KYC must be verified first."
                          }
                          onClick={() => {
                            setActionError("");
                            setPending(purchase);
                          }}
                        >
                          Verify &amp; forward
                        </Button>
                      ) : (
                        <span className="text-xs text-muted">
                          {purchase.status === "PENDING_PAYMENT"
                            ? "Awaiting payment"
                            : "—"}
                        </span>
                      )}
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
        title="Verify and forward"
      >
        {pending && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Forward{" "}
              <strong className="text-ink">{pending.policy.name}</strong> for{" "}
              <strong className="text-ink">
                {pending.customer_name || pending.customer_email}
              </strong>{" "}
              to <strong className="text-ink">{pending.policy.provider.company_name}</strong>?
              This confirms the payment and verified KYC, and sends the purchase to the
              provider for issuance.
            </p>
            <dl className="grid grid-cols-2 gap-2 rounded-xl border border-line bg-surface/40 p-4 text-sm">
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted">Insured</dt>
                <dd className="mt-0.5 text-ink">{pending.kyc?.full_name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted">Bought</dt>
                <dd className="mt-0.5 text-ink">{formatDate(pending.created_at)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted">Premium</dt>
                <dd className="mt-0.5 text-ink">{formatNpr(pending.policy.premium)}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted">Nominee</dt>
                <dd className="mt-0.5 text-ink">{pending.nominee_name || "—"}</dd>
              </div>
            </dl>
            {actionError && <Alert variant="error">{actionError}</Alert>}
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setPending(null)}
                disabled={working}
              >
                Cancel
              </Button>
              <Button variant="cta" onClick={confirm} loading={working}>
                Verify &amp; forward
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
