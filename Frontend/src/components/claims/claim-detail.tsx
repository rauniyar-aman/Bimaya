"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { ClaimDocumentList } from "@/components/claims/claim-document-list";
import { CLAIM_STATUS_META } from "@/components/claims/claim-status";
import { Container } from "@/components/layout/container";
import { Alert } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FileInput } from "@/components/ui/file-input";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { formatDate } from "@/lib/date";
import { formatNpr } from "@/lib/format";
import { ApiError, api, errorMessage, type Claim } from "@/lib/api";

/** Claim documents may be photos or PDFs, up to 10 MB, on resubmission. */
const CLAIM_ACCEPT = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
const CLAIM_MAX_BYTES = 10 * 1024 * 1024;

type State =
  | { phase: "loading" }
  | { phase: "notfound" }
  | { phase: "error" }
  | { phase: "ready"; claim: Claim };

export function ClaimDetail({ id }: { id: string }) {
  const { authFetch } = useAuth();
  const numericId = Number(id);
  const validId = Number.isInteger(numericId) && numericId > 0;
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    if (!validId) return;
    let cancelled = false;
    api.claims
      .get(authFetch, numericId)
      .then((claim) => {
        if (!cancelled) setState({ phase: "ready", claim });
      })
      .catch((error) => {
        if (cancelled) return;
        setState(
          error instanceof ApiError && error.status === 404
            ? { phase: "notfound" }
            : { phase: "error" },
        );
      });
    return () => {
      cancelled = true;
    };
  }, [authFetch, numericId, validId]);

  const resolved: State = validId ? state : { phase: "notfound" };

  return (
    <Container className="flex-1 py-10 lg:py-14">
      <nav aria-label="Breadcrumb" className="text-sm text-muted">
        <Link
          href="/dashboard/claims"
          className="underline-offset-4 transition-colors hover:text-brand-600 hover:underline"
        >
          My claims
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">Claim details</span>
      </nav>

      {resolved.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {resolved.phase === "error" && (
        <Alert variant="error" className="mt-8">
          We could not load this claim. Please refresh and try again.
        </Alert>
      )}

      {resolved.phase === "notfound" && (
        <div className="mt-8 rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
          <h1 className="font-display text-xl font-semibold text-ink">
            Claim not found
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            This claim does not exist or is not on your account.
          </p>
          <Link
            href="/dashboard/claims"
            className={buttonVariants({
              variant: "secondary",
              size: "md",
              className: "mt-5",
            })}
          >
            Back to my claims
          </Link>
        </div>
      )}

      {resolved.phase === "ready" && (
        <ClaimBody
          claim={resolved.claim}
          onUpdated={(claim) => setState({ phase: "ready", claim })}
        />
      )}
    </Container>
  );
}

function ClaimBody({
  claim,
  onUpdated,
}: {
  claim: Claim;
  onUpdated: (claim: Claim) => void;
}) {
  const meta = CLAIM_STATUS_META[claim.status];
  const { policy } = claim.purchase;
  const settledPayout = claim.payouts.find((p) => p.status === "SUCCESS");

  return (
    <>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
          {policy.name}
        </h1>
        <StatusPill status={meta.variant}>{meta.label}</StatusPill>
      </div>
      <p className="mt-1.5 text-sm text-muted">
        {policy.provider.company_name}
        {claim.purchase.policy_number
          ? ` · Policy no. ${claim.purchase.policy_number}`
          : ""}
      </p>

      <Alert variant="info" className="mt-6 max-w-2xl">
        {meta.hint}
      </Alert>

      <div className="mt-6 grid max-w-2xl gap-6">
        {claim.status === "MORE_INFO" && claim.review_note && (
          <Alert variant="error">
            The insurer needs more information: {claim.review_note}
          </Alert>
        )}

        <Card>
          <CardContent className="space-y-5">
            <h2 className="font-display text-lg font-semibold text-ink">
              Claim details
            </h2>
            <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
              <Detail label="Amount claimed">
                {formatNpr(claim.claimed_amount)}
              </Detail>
              <Detail label="Incident date">
                {formatDate(claim.incident_date)}
              </Detail>
              <Detail label="Filed on">{formatDate(claim.created_at)}</Detail>
              {claim.incident_location && (
                <Detail label="Location">{claim.incident_location}</Detail>
              )}
            </dl>
            <div>
              <dt className="text-xs text-muted">What happened</dt>
              <dd className="mt-1 whitespace-pre-line text-sm text-ink">
                {claim.description}
              </dd>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4">
            <div>
              <h2 className="font-display text-lg font-semibold text-ink">
                Documents
              </h2>
              <p className="mt-1 text-sm text-muted">
                The supporting files attached to this claim.
              </p>
            </div>
            <ClaimDocumentList claimId={claim.id} documents={claim.documents} />
          </CardContent>
        </Card>

        {(claim.status === "APPROVED" ||
          claim.status === "SETTLED" ||
          claim.status === "REJECTED") && (
          <Card>
            <CardContent className="space-y-4">
              <h2 className="font-display text-lg font-semibold text-ink">
                Decision
              </h2>
              {claim.status === "REJECTED" ? (
                <p className="text-sm text-ink">
                  This claim was not approved.
                  {claim.review_note ? ` ${claim.review_note}` : ""}
                </p>
              ) : (
                <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
                  <Detail label="Approved amount">
                    {claim.approved_amount
                      ? formatNpr(claim.approved_amount)
                      : "—"}
                  </Detail>
                  <Detail label="Decided on">
                    {formatDate(claim.decided_at)}
                  </Detail>
                  {claim.review_note && (
                    <Detail label="Note">{claim.review_note}</Detail>
                  )}
                </dl>
              )}
            </CardContent>
          </Card>
        )}

        {claim.status === "SETTLED" && settledPayout && (
          <Card>
            <CardContent className="space-y-4">
              <div>
                <h2 className="font-display text-lg font-semibold text-ink">
                  Settlement
                </h2>
                <p className="mt-1 text-sm text-muted">
                  Paid out via a simulated gateway — no real funds are moved in
                  this demo.
                </p>
              </div>
              <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
                <Detail label="Amount paid">
                  {formatNpr(settledPayout.amount)}
                </Detail>
                <Detail label="Gateway">{settledPayout.gateway}</Detail>
                <Detail label="Paid on">
                  {formatDate(settledPayout.paid_at)}
                </Detail>
                <Detail label="Reference">
                  {settledPayout.gateway_reference ?? "—"}
                </Detail>
              </dl>
            </CardContent>
          </Card>
        )}

        {claim.status === "MORE_INFO" && (
          <ResubmitForm claim={claim} onResubmitted={onUpdated} />
        )}
      </div>
    </>
  );
}

interface DocRow {
  key: number;
  file: File | null;
}

function ResubmitForm({
  claim,
  onResubmitted,
}: {
  claim: Claim;
  onResubmitted: (claim: Claim) => void;
}) {
  const { authFetch } = useAuth();
  const [docs, setDocs] = useState<DocRow[]>([{ key: 0, file: null }]);
  const [nextKey, setNextKey] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function setFile(key: number, file: File | null) {
    setDocs((rows) => rows.map((r) => (r.key === key ? { ...r, file } : r)));
  }

  function addRow() {
    setDocs((rows) => [...rows, { key: nextKey, file: null }]);
    setNextKey((k) => k + 1);
  }

  function removeRow(key: number) {
    setDocs((rows) =>
      rows.length === 1 ? rows : rows.filter((r) => r.key !== key),
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    const files = docs.map((r) => r.file).filter((f): f is File => f !== null);
    const form = new FormData();
    for (const file of files) form.append("documents", file);

    setSubmitting(true);
    try {
      const updated = await api.claims.resubmit(authFetch, claim.id, form);
      onResubmitted(updated);
    } catch (err) {
      setError(errorMessage(err, "Could not resubmit your claim. Please try again."));
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardContent className="space-y-4">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">
            Respond to the insurer
          </h2>
          <p className="mt-1 text-sm text-muted">
            Attach any additional documents the insurer asked for, then send your
            claim back for review.
          </p>
        </div>
        {error && <Alert variant="error">{error}</Alert>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-3">
            {docs.map((row, index) => (
              <div key={row.key}>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-sm font-medium text-ink">
                    Document {index + 1}
                  </span>
                  {docs.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeRow(row.key)}
                      disabled={submitting}
                      className="text-sm font-medium text-muted underline-offset-4 hover:text-red-600 hover:underline disabled:opacity-60"
                    >
                      Remove
                    </button>
                  )}
                </div>
                <FileInput
                  id={`resubmit_doc_${row.key}`}
                  onFile={(file) => setFile(row.key, file)}
                  disabled={submitting}
                  accept={CLAIM_ACCEPT}
                  maxBytes={CLAIM_MAX_BYTES}
                />
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2.5">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={addRow}
              disabled={submitting}
            >
              + Add another document
            </Button>
          </div>
          <Button type="submit" loading={submitting}>
            Resubmit for review
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Detail({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 font-display font-semibold text-ink">{children}</dd>
    </div>
  );
}
