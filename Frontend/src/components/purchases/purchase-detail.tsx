"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Container } from "@/components/layout/container";
import { PURCHASE_STATUS_META } from "@/components/purchases/purchase-status";
import { Alert } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { StatusPill } from "@/components/ui/status-pill";
import { formatDate } from "@/lib/date";
import { formatFrequency, formatNpr, formatTerm } from "@/lib/format";
import { saveBlob } from "@/lib/download";
import { ApiError, api, errorMessage, type PolicyPurchase } from "@/lib/api";

type State =
  | { phase: "loading" }
  | { phase: "notfound" }
  | { phase: "error" }
  | { phase: "ready"; purchase: PolicyPurchase };

export function PurchaseDetail({ id }: { id: string }) {
  const { authFetch } = useAuth();
  const numericId = Number(id);
  const validId = Number.isInteger(numericId) && numericId > 0;
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    if (!validId) return;
    let cancelled = false;
    api.purchases
      .get(authFetch, numericId)
      .then((purchase) => {
        if (!cancelled) setState({ phase: "ready", purchase });
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
          href="/dashboard/policies"
          className="underline-offset-4 transition-colors hover:text-brand-600 hover:underline"
        >
          My policies
        </Link>
        <span aria-hidden="true"> / </span>
        <span className="text-ink">Policy details</span>
      </nav>

      {resolved.phase === "loading" && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6 text-brand-500" />
        </div>
      )}

      {resolved.phase === "error" && (
        <Alert variant="error" className="mt-8">
          We could not load this policy. Please refresh and try again.
        </Alert>
      )}

      {resolved.phase === "notfound" && (
        <div className="mt-8 rounded-2xl border border-dashed border-line bg-surface/50 p-12 text-center">
          <h1 className="font-display text-xl font-semibold text-ink">
            Policy not found
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm text-muted">
            This policy does not exist or is not on your account.
          </p>
          <Link
            href="/dashboard/policies"
            className={buttonVariants({
              variant: "secondary",
              size: "md",
              className: "mt-5",
            })}
          >
            Back to my policies
          </Link>
        </div>
      )}

      {resolved.phase === "ready" && (
        <PurchaseBody
          purchase={resolved.purchase}
          onCancelled={(updated) => setState({ phase: "ready", purchase: updated })}
        />
      )}
    </Container>
  );
}

function PurchaseBody({
  purchase,
  onCancelled,
}: {
  purchase: PolicyPurchase;
  onCancelled: (updated: PolicyPurchase) => void;
}) {
  const { authFetch } = useAuth();
  const { policy } = purchase;
  const meta = PURCHASE_STATUS_META[purchase.status];

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [downloading, setDownloading] = useState<
    null | "certificate" | "receipt"
  >(null);
  const [docError, setDocError] = useState("");

  // The certificate exists once a policy number has been issued; a receipt
  // exists once a payment has succeeded (every status past pending, except a
  // cancelled purchase — which can only be cancelled before it is ever paid).
  const canDownloadCertificate = Boolean(purchase.policy_number);
  const canDownloadReceipt =
    purchase.status !== "PENDING_PAYMENT" && purchase.status !== "CANCELLED";
  const hasDocuments = canDownloadCertificate || canDownloadReceipt;

  async function handleCancel() {
    if (
      !window.confirm(
        `Cancel your purchase of "${policy.name}"? This cannot be undone.`,
      )
    )
      return;
    setError("");
    setBusy(true);
    try {
      const updated = await api.purchases.cancel(authFetch, purchase.id);
      onCancelled(updated);
    } catch (err) {
      setError(errorMessage(err, "Could not cancel this purchase."));
      setBusy(false);
    }
  }

  async function handleDownload(kind: "certificate" | "receipt") {
    setDocError("");
    setDownloading(kind);
    try {
      if (kind === "certificate") {
        const blob = await api.purchases.certificate(authFetch, purchase.id);
        saveBlob(blob, `Bimaya-Policy-${purchase.policy_number}.pdf`);
      } else {
        const blob = await api.purchases.receipt(authFetch, purchase.id);
        saveBlob(blob, `Bimaya-Receipt-${purchase.policy_number ?? purchase.id}.pdf`);
      }
    } catch (err) {
      setDocError(errorMessage(err, `Could not download the ${kind}.`));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
          {policy.name}
        </h1>
        <StatusPill status={meta.variant}>{meta.label}</StatusPill>
      </div>
      <p className="mt-1.5 text-sm text-muted">{policy.provider.company_name}</p>

      <Alert variant="info" className="mt-6 max-w-2xl">
        {meta.hint}
      </Alert>

      <div className="mt-6 grid max-w-2xl gap-6">
        <Card>
          <CardContent className="space-y-5">
            <h2 className="font-display text-lg font-semibold text-ink">
              Cover
            </h2>
            <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
              <Detail label="Premium">
                {formatNpr(policy.premium)}{" "}
                <span className="text-xs font-normal text-muted">
                  · {formatFrequency(policy.premium_frequency)}
                </span>
              </Detail>
              <Detail label="Coverage">{formatNpr(policy.coverage_amount)}</Detail>
              <Detail label="Term">{formatTerm(policy.term_months)}</Detail>
              {purchase.status === "ACTIVE" && (
                <>
                  <Detail label="Policy number">
                    {purchase.policy_number ?? "—"}
                  </Detail>
                  <Detail label="Cover starts">
                    {formatDate(purchase.start_date)}
                  </Detail>
                  <Detail label="Cover ends">
                    {formatDate(purchase.end_date)}
                  </Detail>
                </>
              )}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-5">
            <h2 className="font-display text-lg font-semibold text-ink">
              Nominee
            </h2>
            <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
              <Detail label="Name">{purchase.nominee_name}</Detail>
              <Detail label="Relationship">
                {purchase.nominee_relationship}
              </Detail>
              <Detail label="Contact">{purchase.nominee_contact}</Detail>
            </dl>
          </CardContent>
        </Card>

        {hasDocuments && (
          <Card>
            <CardContent className="space-y-4">
              <div>
                <h2 className="font-display text-lg font-semibold text-ink">
                  Documents
                </h2>
                <p className="mt-1 text-sm text-muted">
                  Download your policy paperwork as PDF.
                </p>
              </div>
              {docError && <Alert variant="error">{docError}</Alert>}
              <div className="flex flex-wrap gap-2.5">
                {canDownloadCertificate && (
                  <Button
                    variant="primary"
                    onClick={() => handleDownload("certificate")}
                    loading={downloading === "certificate"}
                    disabled={downloading !== null}
                  >
                    Download certificate (PDF)
                  </Button>
                )}
                {canDownloadReceipt && (
                  <Button
                    variant="secondary"
                    onClick={() => handleDownload("receipt")}
                    loading={downloading === "receipt"}
                    disabled={downloading !== null}
                  >
                    Download receipt (PDF)
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {purchase.status === "ACTIVE" && (
          <Card>
            <CardContent className="space-y-4">
              <div>
                <h2 className="font-display text-lg font-semibold text-ink">
                  Need to make a claim?
                </h2>
                <p className="mt-1 text-sm text-muted">
                  If something covered by this policy has happened, file a claim
                  and track it through to settlement.
                </p>
              </div>
              <Link
                href={`/dashboard/claims/new?purchase=${purchase.id}`}
                className={buttonVariants({ variant: "cta", size: "md" })}
              >
                File a claim
              </Link>
            </CardContent>
          </Card>
        )}

        {purchase.status === "PENDING_PAYMENT" && (
          <Card>
            <CardContent className="space-y-4">
              <div>
                <h2 className="font-display text-lg font-semibold text-ink">
                  Finish paying
                </h2>
                <p className="mt-1 text-sm text-muted">
                  This policy is not active yet. Complete payment to switch your
                  cover on, or cancel if you have changed your mind.
                </p>
              </div>
              {error && <Alert variant="error">{error}</Alert>}
              <div className="flex flex-wrap gap-2.5">
                <Link
                  href={`/checkout/${policy.slug}`}
                  className={buttonVariants({ variant: "cta", size: "md" })}
                >
                  Complete payment
                </Link>
                <Button
                  variant="secondary"
                  onClick={handleCancel}
                  loading={busy}
                  disabled={busy}
                >
                  Cancel purchase
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </>
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
