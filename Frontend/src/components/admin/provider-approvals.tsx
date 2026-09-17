"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { PROVIDER_FILTERS } from "@/components/admin/filters";
import { KYC_STATUS_META } from "@/components/admin/status-meta";
import { ExportButton } from "@/components/admin/export-button";
import { ProviderMembersModal } from "@/components/admin/provider-members";
import { ProviderKycModal } from "@/components/admin/provider-kyc";
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
import { api, errorMessage, type AdminProvider, type Paginated } from "@/lib/api";
import { formatDate } from "@/lib/date";
import { useDebouncedValue } from "@/lib/use-debounced-value";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<AdminProvider> };

type Pending = { provider: AdminProvider; action: "approve" | "revoke" };

/** Admin table of providers with approve / revoke controls. */
export function ProviderApprovals() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [approved, setApproved] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  const [pending, setPending] = useState<Pending | null>(null);
  const [working, setWorking] = useState(false);
  const [actionError, setActionError] = useState("");

  const [members, setMembers] = useState<AdminProvider | null>(null);
  const [kycFor, setKycFor] = useState<AdminProvider | null>(null);

  // Commission-rate editor
  const [commissionFor, setCommissionFor] = useState<AdminProvider | null>(null);
  const [rateInput, setRateInput] = useState("");
  const [savingRate, setSavingRate] = useState(false);
  const [rateError, setRateError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listProviders(authFetch, {
        page,
        is_approved: approved === "" ? undefined : approved === "true",
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
  }, [authFetch, page, approved, debouncedSearch]);

  function updateRow(updated: AdminProvider) {
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
      const updated =
        pending.action === "approve"
          ? await api.admin.approveProvider(authFetch, pending.provider.id)
          : await api.admin.revokeProvider(authFetch, pending.provider.id);
      updateRow(updated);
      setPending(null);
    } catch (error) {
      setActionError(errorMessage(error, "Could not update this provider."));
    } finally {
      setWorking(false);
    }
  }

  function openCommission(provider: AdminProvider) {
    setRateError("");
    setRateInput(provider.commission_rate);
    setCommissionFor(provider);
  }

  async function saveCommission() {
    if (!commissionFor) return;
    setSavingRate(true);
    setRateError("");
    try {
      const updated = await api.admin.setProviderCommission(
        authFetch,
        commissionFor.id,
        rateInput.trim(),
      );
      updateRow(updated);
      setCommissionFor(null);
    } catch (error) {
      setRateError(errorMessage(error, "Enter a rate between 0 and 100."));
    } finally {
      setSavingRate(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-display text-xl font-semibold text-ink">Providers</h2>
        <div className="flex gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search company or email"
              className="w-56 pl-9"
              aria-label="Search providers"
            />
          </div>
          <Select
            value={approved}
            onChange={(e) => {
              setPage(1);
              setApproved(e.target.value);
            }}
            className="w-44"
            aria-label="Filter by approval"
          >
            {PROVIDER_FILTERS.map((o) => (
              <option key={o.label} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
          <ExportButton
            filename="bimaya-providers.csv"
            onExport={() =>
              api.admin.exportProviders(authFetch, {
                is_approved: approved === "" ? undefined : approved === "true",
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
          We could not load providers. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <EmptyRow label="No providers match your filters." />
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <>
          <Table>
            <THead>
              <TR>
                <TH>Company</TH>
                <TH>Owner</TH>
                <TH>KYC</TH>
                <TH className="text-center">Policies</TH>
                <TH className="text-center">Commission</TH>
                <TH>Status</TH>
                <TH className="text-right">Action</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((provider) => {
                const kyc = KYC_STATUS_META[provider.kyc_status];
                return (
                  <TR key={provider.id}>
                    <TD>
                      <Link
                        href={`/admin/providers/${provider.id}`}
                        className="font-medium text-ink underline-offset-4 transition-colors hover:text-brand-600 hover:underline"
                      >
                        {provider.company_name}
                      </Link>
                      <div className="text-xs text-muted">
                        <span className="font-mono">{provider.public_id}</span> ·
                        Joined {formatDate(provider.created_at)}
                      </div>
                    </TD>
                    <TD>
                      <div className="text-ink">{provider.owner_name || "—"}</div>
                      <div className="text-xs text-muted">{provider.owner_email}</div>
                    </TD>
                    <TD>
                      <StatusPill status={kyc.variant}>{kyc.label}</StatusPill>
                    </TD>
                    <TD className="text-center">{provider.policy_count}</TD>
                    <TD className="text-center tabular-nums">
                      {provider.commission_rate}%
                    </TD>
                    <TD>
                      <StatusPill status={provider.is_approved ? "active" : "pending"}>
                        {provider.is_approved ? "Approved" : "Awaiting"}
                      </StatusPill>
                    </TD>
                    <TD className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setMembers(provider)}
                        >
                          Team
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setKycFor(provider)}
                        >
                          KYC
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => openCommission(provider)}
                        >
                          Rate
                        </Button>
                        {provider.is_approved ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setActionError("");
                              setPending({ provider, action: "revoke" });
                            }}
                          >
                            Revoke
                          </Button>
                        ) : (
                          <Button
                            variant="success"
                            size="sm"
                            onClick={() => {
                              setActionError("");
                              setPending({ provider, action: "approve" });
                            }}
                          >
                            Approve
                          </Button>
                        )}
                      </div>
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>

          <Pagination
            page={page}
            count={state.data.count}
            onChange={setPage}
          />
        </>
      )}

      <Modal
        open={pending !== null}
        onClose={() => (working ? undefined : setPending(null))}
        title={pending?.action === "approve" ? "Approve provider" : "Revoke approval"}
      >
        {pending && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              {pending.action === "approve" ? (
                <>
                  Approve <strong className="text-ink">{pending.provider.company_name}</strong>?
                  Their published policies go live on the marketplace and they can
                  issue forwarded purchases.
                </>
              ) : (
                <>
                  Revoke approval for{" "}
                  <strong className="text-ink">{pending.provider.company_name}</strong>?
                  Their policies stop appearing publicly until re-approved.
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
                variant={pending.action === "approve" ? "success" : "primary"}
                onClick={confirm}
                loading={working}
              >
                {pending.action === "approve" ? "Approve" : "Revoke"}
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {members && (
        <ProviderMembersModal
          provider={members}
          open={members !== null}
          onClose={() => setMembers(null)}
        />
      )}

      {kycFor && (
        <ProviderKycModal
          provider={kycFor}
          open={kycFor !== null}
          onClose={() => setKycFor(null)}
        />
      )}

      <Modal
        open={commissionFor !== null}
        onClose={() => (savingRate ? undefined : setCommissionFor(null))}
        title="Set commission rate"
      >
        {commissionFor && (
          <div className="space-y-4">
            <p className="text-sm text-muted">
              Platform commission charged on each sale of{" "}
              <strong className="text-ink">{commissionFor.company_name}</strong>
              &apos;s policies. This applies to future issuances only — existing
              payouts keep the rate recorded when they were created.
            </p>
            <div>
              <label
                htmlFor="commission-rate"
                className="mb-1 block text-sm font-medium text-ink"
              >
                Commission percent
              </label>
              <div className="flex items-center gap-2">
                <Input
                  id="commission-rate"
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  inputMode="decimal"
                  value={rateInput}
                  onChange={(e) => setRateInput(e.target.value)}
                  className="w-32"
                  aria-label="Commission percent"
                />
                <span className="text-muted">%</span>
              </div>
            </div>
            {rateError && <Alert variant="error">{rateError}</Alert>}
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => setCommissionFor(null)}
                disabled={savingRate}
              >
                Cancel
              </Button>
              <Button onClick={saveCommission} loading={savingRate}>
                Save commission
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

function EmptyRow({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
      {label}
    </div>
  );
}
