"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { KYC_FILTERS } from "@/components/admin/filters";
import { KYC_STATUS_META } from "@/components/admin/status-meta";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { Textarea } from "@/components/ui/textarea";
import { SearchIcon } from "@/components/icons";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  api,
  errorMessage,
  fieldErrors,
  type AdminKyc,
  type KycStatus,
  type Paginated,
} from "@/lib/api";
import { formatDate } from "@/lib/date";
import { useDebouncedValue } from "@/lib/use-debounced-value";

type State =
  | { phase: "loading" }
  | { phase: "error" }
  | { phase: "ready"; data: Paginated<AdminKyc> };

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  PASSPORT: "Passport",
  CITIZENSHIP: "Citizenship",
  NID: "National ID",
};

/** Admin KYC queue: review records, view documents, verify or reject. */
export function KycReview() {
  const { authFetch } = useAuth();
  const [state, setState] = useState<State>({ phase: "loading" });
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [active, setActive] = useState<AdminKyc | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.admin
      .listKyc(authFetch, {
        page,
        status: (statusFilter || undefined) as KycStatus | undefined,
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

  function applyStatus(id: number, status: KycStatus, review_note: string) {
    setState((prev) =>
      prev.phase === "ready"
        ? {
            phase: "ready",
            data: {
              ...prev.data,
              results: prev.data.results.map((k) =>
                k.id === id ? { ...k, status, review_note } : k,
              ),
            },
          }
        : prev,
    );
    setActive((prev) => (prev && prev.id === id ? { ...prev, status, review_note } : prev));
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="font-display text-xl font-semibold text-ink">KYC review</h2>
        <div className="flex gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <Input
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
              placeholder="Search name, email, document"
              className="w-64 pl-9"
              aria-label="Search KYC records"
            />
          </div>
          <Select
            value={statusFilter}
            onChange={(e) => {
              setPage(1);
              setStatusFilter(e.target.value);
            }}
            className="w-40"
            aria-label="Filter by status"
          >
            {KYC_FILTERS.map((o) => (
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
          We could not load KYC records. Please refresh and try again.
        </Alert>
      )}

      {state.phase === "ready" && state.data.results.length === 0 && (
        <div className="rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center text-sm text-muted">
          No KYC records match your filters.
        </div>
      )}

      {state.phase === "ready" && state.data.results.length > 0 && (
        <>
          <Table>
            <THead>
              <TR>
                <TH>Applicant</TH>
                <TH>Customer</TH>
                <TH>Document</TH>
                <TH>For</TH>
                <TH>Status</TH>
                <TH className="text-right">Action</TH>
              </TR>
            </THead>
            <TBody>
              {state.data.results.map((kyc) => {
                const meta = KYC_STATUS_META[kyc.status];
                return (
                  <TR key={kyc.id}>
                    <TD>
                      <div className="font-medium text-ink">{kyc.full_name}</div>
                      <div className="text-xs text-muted">
                        Submitted {formatDate(kyc.created_at)}
                      </div>
                    </TD>
                    <TD className="text-muted">{kyc.customer_email}</TD>
                    <TD>
                      <div className="text-ink">
                        {DOCUMENT_TYPE_LABELS[kyc.document_type] ?? kyc.document_type}
                      </div>
                      <div className="text-xs text-muted">{kyc.document_number}</div>
                    </TD>
                    <TD className="text-muted">
                      {kyc.is_self ? "Self" : "Beneficiary"}
                    </TD>
                    <TD>
                      <StatusPill status={meta.variant}>{meta.label}</StatusPill>
                    </TD>
                    <TD className="text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setActive(kyc)}
                      >
                        Review
                      </Button>
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>

          <Pagination page={page} count={state.data.count} onChange={setPage} />
        </>
      )}

      <KycReviewModal
        key={active?.id ?? "none"}
        kyc={active}
        onClose={() => setActive(null)}
        onDecided={applyStatus}
      />
    </div>
  );
}

function KycReviewModal({
  kyc,
  onClose,
  onDecided,
}: {
  kyc: AdminKyc | null;
  onClose: () => void;
  onDecided: (id: number, status: KycStatus, note: string) => void;
}) {
  const { authFetch } = useAuth();
  const [mode, setMode] = useState<"view" | "reject">("view");
  const [note, setNote] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [noteError, setNoteError] = useState("");

  if (!kyc) return null;

  const meta = KYC_STATUS_META[kyc.status];

  async function verify() {
    if (!kyc) return;
    setWorking(true);
    setError("");
    try {
      await api.admin.verifyKyc(authFetch, kyc.id);
      onDecided(kyc.id, "VERIFIED", kyc.review_note);
      onClose();
    } catch (err) {
      setError(errorMessage(err, "Could not verify this KYC."));
    } finally {
      setWorking(false);
    }
  }

  async function reject() {
    if (!kyc) return;
    setWorking(true);
    setError("");
    setNoteError("");
    try {
      await api.admin.rejectKyc(authFetch, kyc.id, note.trim());
      onDecided(kyc.id, "REJECTED", note.trim());
      onClose();
    } catch (err) {
      setNoteError(fieldErrors(err).note ?? "");
      setError(errorMessage(err, "Could not reject this KYC."));
    } finally {
      setWorking(false);
    }
  }

  const decided = kyc.status !== "PENDING";

  return (
    <Modal open={kyc !== null} onClose={() => (working ? undefined : onClose())} title="KYC review">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-display text-lg font-semibold text-ink">
              {kyc.full_name}
            </p>
            <p className="text-xs text-muted">{kyc.customer_email}</p>
          </div>
          <StatusPill status={meta.variant}>{meta.label}</StatusPill>
        </div>

        <dl className="grid gap-x-6 gap-y-2 rounded-xl border border-line bg-surface/40 p-4 text-sm sm:grid-cols-2">
          <Detail label="Document">
            {DOCUMENT_TYPE_LABELS[kyc.document_type] ?? kyc.document_type} ·{" "}
            {kyc.document_number}
          </Detail>
          <Detail label="For">{kyc.is_self ? "Self" : "Beneficiary"}</Detail>
          <Detail label="Phone">{kyc.phone || "—"}</Detail>
          <Detail label="Date of birth">{formatDate(kyc.date_of_birth)}</Detail>
          <Detail label="Permanent address">{kyc.permanent_address || "—"}</Detail>
          <Detail label="Temporary address">{kyc.temporary_address || "—"}</Detail>
        </dl>

        <div className="grid gap-3 sm:grid-cols-2">
          <KycDocument kyc={kyc} side="front" available={kyc.has_front} />
          <KycDocument kyc={kyc} side="back" available={kyc.has_back} />
        </div>

        {kyc.review_note && (
          <Alert variant="info">
            <span className="font-medium">Review note:</span> {kyc.review_note}
          </Alert>
        )}

        {error && <Alert variant="error">{error}</Alert>}

        {mode === "reject" ? (
          <Field label="Reason for rejection" htmlFor="kyc-reject-note" error={noteError}>
            <Textarea
              id="kyc-reject-note"
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Tell the customer what to fix and resubmit."
              disabled={working}
            />
          </Field>
        ) : null}

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          {mode === "reject" ? (
            <>
              <Button variant="secondary" onClick={() => setMode("view")} disabled={working}>
                Back
              </Button>
              <Button variant="primary" onClick={reject} loading={working} disabled={!note.trim()}>
                Confirm rejection
              </Button>
            </>
          ) : (
            <>
              <Button variant="secondary" onClick={onClose} disabled={working}>
                Close
              </Button>
              <Button
                variant="outline"
                onClick={() => setMode("reject")}
                disabled={working || decided}
              >
                Reject
              </Button>
              <Button
                variant="success"
                onClick={verify}
                loading={working}
                disabled={decided}
              >
                Verify
              </Button>
            </>
          )}
        </div>
      </div>
    </Modal>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-ink">{children}</dd>
    </div>
  );
}

/**
 * A KYC document image. These are PII, so the bytes are pulled through the
 * authenticated admin endpoint into an object URL rather than linked from a
 * raw media path. The URL is revoked when the component unmounts or the record
 * changes.
 */
function KycDocument({
  kyc,
  side,
  available,
}: {
  kyc: AdminKyc;
  side: "front" | "back";
  available: boolean;
}) {
  const { authFetch } = useAuth();
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!available) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    api.admin
      .kycDocument(authFetch, kyc.id, side)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setUrl(null);
    };
  }, [authFetch, kyc.id, side, available]);

  const label = side === "front" ? "Document front" : "Document back";

  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className="border-b border-line bg-surface/60 px-3 py-2 text-xs font-medium text-muted">
        {label}
      </div>
      <div className="flex aspect-[3/2] items-center justify-center bg-surface/30">
        {!available ? (
          <span className="text-xs text-muted">Not provided</span>
        ) : failed ? (
          <span className="text-xs text-danger">Could not load</span>
        ) : url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={label} className="h-full w-full object-contain" />
        ) : (
          <Spinner className="h-5 w-5 text-brand-500" />
        )}
      </div>
    </div>
  );
}
